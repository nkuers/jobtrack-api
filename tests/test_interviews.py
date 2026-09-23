from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.models.interview import Interview
from app.models.user import User
from app.schemas.interview import InterviewCreate
from app.services.application_service import APPLICATION_HAS_INTERVIEWS
from app.services.interview_service import (
    FEEDBACK_REQUIRES_COMPLETED,
    INTERVIEW_CONFLICT,
    INVALID_INTERVIEW_STATUS,
    InterviewService,
)


def headers_for(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.username})
    return {"Authorization": f"Bearer {token}"}


def create_application(
    client: TestClient,
    headers: dict[str, str],
    suffix: str,
) -> dict:
    company = client.post(
        "/api/v1/companies",
        headers=headers,
        json={"name": f"Interview Company {suffix}"},
    )
    assert company.status_code == 201, company.text
    job = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "company_id": company.json()["id"],
            "title": f"Interview Job {suffix}",
        },
    )
    assert job.status_code == 201, job.text
    application = client.post(
        "/api/v1/applications",
        headers=headers,
        json={"job_id": job.json()["id"], "status": "applied"},
    )
    assert application.status_code == 201, application.text
    return application.json()


def create_interview(
    client: TestClient,
    headers: dict[str, str],
    application_id: int,
    scheduled_at: datetime,
    **overrides,
) -> dict:
    payload = {
        "application_id": application_id,
        "interview_type": "technical",
        "scheduled_at": scheduled_at.isoformat(),
        "duration_minutes": 60,
        "meeting_url": "https://meet.example.com/interview",
        "notes": "Prepare examples",
        **overrides,
    }
    response = client.post("/api/v1/interviews", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_interview_endpoints_require_authentication(client: TestClient):
    assert client.get("/api/v1/interviews").status_code == 401
    assert client.get("/api/v1/interviews/upcoming").status_code == 401
    assert (
        client.post(
            "/api/v1/interviews",
            json={
                "application_id": 1,
                "interview_type": "technical",
                "scheduled_at": "2026-10-01T10:00:00Z",
            },
        ).status_code
        == 401
    )


def test_create_interview_requires_owned_application_and_binds_owner(
    client: TestClient,
    db_session: Session,
    user: User,
    second_user: User,
    auth_headers: dict[str, str],
):
    other_application = create_application(
        client,
        headers_for(second_user),
        "Other Owner",
    )
    rejected = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={
            "application_id": other_application["id"],
            "interview_type": "technical",
            "scheduled_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
    )
    assert rejected.status_code == 404
    assert rejected.json() == {"detail": "Application not found"}

    application = create_application(client, auth_headers, "Own")
    injected = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={
            "application_id": application["id"],
            "interview_type": "technical",
            "scheduled_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "owner_id": second_user.id,
        },
    )
    assert injected.status_code == 422

    created = create_interview(
        client,
        auth_headers,
        application["id"],
        datetime.now(UTC) + timedelta(days=2),
    )
    interview = db_session.get(Interview, created["id"])
    assert "owner_id" not in created
    assert interview is not None
    assert interview.owner_id == user.id


def test_timezone_is_required_and_normalized_to_utc(
    client: TestClient,
    auth_headers: dict[str, str],
):
    application = create_application(client, auth_headers, "Timezone")
    naive = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={
            "application_id": application["id"],
            "interview_type": "phone_screen",
            "scheduled_at": "2026-10-01T10:00:00",
        },
    )
    assert naive.status_code == 422

    created = create_interview(
        client,
        auth_headers,
        application["id"],
        datetime.fromisoformat("2026-10-01T10:00:00+08:00"),
    )
    returned = datetime.fromisoformat(created["scheduled_at"].replace("Z", "+00:00"))
    assert returned == datetime(2026, 10, 1, 2, tzinfo=UTC)


@pytest.mark.parametrize(
    "overrides",
    [
        {"duration_minutes": 14},
        {"duration_minutes": 481},
        {"interview_type": "unknown"},
        {"status": "completed"},
        {"feedback": "Too early"},
        {"location": "x" * 256},
    ],
)
def test_interview_input_validation(
    client: TestClient,
    auth_headers: dict[str, str],
    overrides: dict,
):
    application = create_application(client, auth_headers, "Validation")
    response = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={
            "application_id": application["id"],
            "interview_type": "technical",
            "scheduled_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
            **overrides,
        },
    )
    assert response.status_code == 422


def test_scheduled_interviews_cannot_overlap_for_same_user(
    client: TestClient,
    auth_headers: dict[str, str],
):
    first_application = create_application(client, auth_headers, "Overlap One")
    second_application = create_application(client, auth_headers, "Overlap Two")
    start = datetime.now(UTC) + timedelta(days=4)
    first = create_interview(
        client,
        auth_headers,
        first_application["id"],
        start,
        duration_minutes=60,
    )

    overlap = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={
            "application_id": second_application["id"],
            "interview_type": "behavioral",
            "scheduled_at": (start + timedelta(minutes=30)).isoformat(),
            "duration_minutes": 30,
        },
    )
    assert overlap.status_code == 409
    assert overlap.json() == {"detail": INTERVIEW_CONFLICT}

    boundary = create_interview(
        client,
        auth_headers,
        second_application["id"],
        start + timedelta(minutes=60),
        duration_minutes=30,
    )
    assert boundary["id"] != first["id"]


def test_different_users_may_schedule_the_same_time(
    client: TestClient,
    second_user: User,
    auth_headers: dict[str, str],
):
    second_headers = headers_for(second_user)
    own_application = create_application(client, auth_headers, "Shared Time One")
    other_application = create_application(client, second_headers, "Shared Time Two")
    start = datetime.now(UTC) + timedelta(days=5)

    create_interview(client, auth_headers, own_application["id"], start)
    created = create_interview(client, second_headers, other_application["id"], start)
    assert created["status"] == "scheduled"


def test_update_complete_feedback_and_status_rules(
    client: TestClient,
    auth_headers: dict[str, str],
):
    application = create_application(client, auth_headers, "Status")
    interview = create_interview(
        client,
        auth_headers,
        application["id"],
        datetime.now(UTC) + timedelta(days=6),
    )
    path = f"/api/v1/interviews/{interview['id']}"

    premature = client.patch(path, headers=auth_headers, json={"feedback": "Great"})
    assert premature.status_code == 409
    assert premature.json() == {"detail": FEEDBACK_REQUIRES_COMPLETED}

    completed = client.patch(
        path,
        headers=auth_headers,
        json={"status": "completed", "feedback": " Strong technical round "},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["feedback"] == "Strong technical round"

    reopened = client.patch(path, headers=auth_headers, json={"status": "scheduled"})
    assert reopened.status_code == 409
    assert reopened.json() == {"detail": INVALID_INTERVIEW_STATUS}


def test_cancelled_interview_releases_time_slot(
    client: TestClient,
    auth_headers: dict[str, str],
):
    first_application = create_application(client, auth_headers, "Cancel One")
    second_application = create_application(client, auth_headers, "Cancel Two")
    start = datetime.now(UTC) + timedelta(days=7)
    interview = create_interview(
        client,
        auth_headers,
        first_application["id"],
        start,
    )
    cancelled = client.patch(
        f"/api/v1/interviews/{interview['id']}",
        headers=auth_headers,
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200

    replacement = create_interview(
        client,
        auth_headers,
        second_application["id"],
        start,
    )
    assert replacement["status"] == "scheduled"


def test_upcoming_is_owner_scoped_excludes_cancelled_and_is_stably_sorted(
    client: TestClient,
    second_user: User,
    auth_headers: dict[str, str],
):
    now = datetime.now(UTC)
    application = create_application(client, auth_headers, "Upcoming")
    later = create_interview(
        client,
        auth_headers,
        application["id"],
        now + timedelta(days=3),
    )
    earlier = create_interview(
        client,
        auth_headers,
        application["id"],
        now + timedelta(days=2),
    )
    cancelled = create_interview(
        client,
        auth_headers,
        application["id"],
        now + timedelta(days=4),
    )
    client.patch(
        f"/api/v1/interviews/{cancelled['id']}",
        headers=auth_headers,
        json={"status": "cancelled"},
    )
    create_interview(
        client,
        auth_headers,
        application["id"],
        now - timedelta(days=1),
    )

    other_headers = headers_for(second_user)
    other_application = create_application(client, other_headers, "Other Upcoming")
    create_interview(
        client,
        other_headers,
        other_application["id"],
        now + timedelta(days=1),
    )

    response = client.get("/api/v1/interviews/upcoming", headers=auth_headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [earlier["id"], later["id"]]


def test_list_filters_by_application_and_status(
    client: TestClient,
    auth_headers: dict[str, str],
):
    first_application = create_application(client, auth_headers, "Filter One")
    second_application = create_application(client, auth_headers, "Filter Two")
    start = datetime.now(UTC) + timedelta(days=8)
    first = create_interview(
        client,
        auth_headers,
        first_application["id"],
        start,
    )
    second = create_interview(
        client,
        auth_headers,
        second_application["id"],
        start + timedelta(hours=2),
    )
    client.patch(
        f"/api/v1/interviews/{second['id']}",
        headers=auth_headers,
        json={"status": "cancelled"},
    )

    by_application = client.get(
        "/api/v1/interviews",
        headers=auth_headers,
        params={"application_id": first_application["id"]},
    )
    assert by_application.json()["total"] == 1
    assert by_application.json()["items"][0]["id"] == first["id"]

    cancelled = client.get(
        "/api/v1/interviews",
        headers=auth_headers,
        params={"status": "cancelled"},
    )
    assert [item["id"] for item in cancelled.json()["items"]] == [second["id"]]


def test_interview_crud_is_owner_scoped(
    client: TestClient,
    second_user: User,
    auth_headers: dict[str, str],
):
    other_headers = headers_for(second_user)
    application = create_application(client, other_headers, "Private")
    interview = create_interview(
        client,
        other_headers,
        application["id"],
        datetime.now(UTC) + timedelta(days=9),
    )
    path = f"/api/v1/interviews/{interview['id']}"

    for response in (
        client.get(path, headers=auth_headers),
        client.patch(path, headers=auth_headers, json={"location": "Remote"}),
        client.delete(path, headers=auth_headers),
    ):
        assert response.status_code == 404
        assert response.json() == {"detail": "Interview not found"}

    updated = client.patch(path, headers=other_headers, json={"location": " Remote "})
    assert updated.status_code == 200
    assert updated.json()["location"] == "Remote"
    assert client.delete(path, headers=other_headers).status_code == 204
    assert client.get(path, headers=other_headers).status_code == 404


def test_application_with_interview_cannot_be_deleted(
    client: TestClient,
    auth_headers: dict[str, str],
):
    application = create_application(client, auth_headers, "Delete Constraint")
    interview = create_interview(
        client,
        auth_headers,
        application["id"],
        datetime.now(UTC) + timedelta(days=10),
    )

    conflict = client.delete(
        f"/api/v1/applications/{application['id']}",
        headers=auth_headers,
    )
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": APPLICATION_HAS_INTERVIEWS}

    assert (
        client.delete(
            f"/api/v1/interviews/{interview['id']}",
            headers=auth_headers,
        ).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/v1/applications/{application['id']}",
            headers=auth_headers,
        ).status_code
        == 204
    )


def test_interview_service_rolls_back_on_write_failure():
    db = MagicMock()
    db.commit.side_effect = RuntimeError("database unavailable")
    service = InterviewService(db)
    service.repository = MagicMock()
    service.application_repository = MagicMock()
    service.application_repository.get_owned.return_value = object()
    service.repository.has_overlap.return_value = False

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.create(
            1,
            InterviewCreate(
                application_id=1,
                interview_type="technical",
                scheduled_at=datetime.now(UTC) + timedelta(days=1),
            ),
        )

    db.rollback.assert_called_once_with()
