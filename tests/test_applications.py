from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Barrier
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.db.session import SessionLocal
from app.exceptions.domain import ResourceConflictError
from app.models.application import Application
from app.models.application_status_history import ApplicationStatusHistory
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationStatus
from app.services.application_service import (
    APPLICATION_CONFLICT,
    INVALID_APPLICATION_DATES,
    INVALID_STATUS_TRANSITION,
    ApplicationService,
)
from app.services.job_service import JOB_HAS_APPLICATIONS


def headers_for(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.username})
    return {"Authorization": f"Bearer {token}"}


def create_company(
    client: TestClient,
    headers: dict[str, str],
    name: str,
) -> dict:
    response = client.post(
        "/api/v1/companies",
        headers=headers,
        json={"name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_job(
    client: TestClient,
    headers: dict[str, str],
    company_id: int,
    title: str,
) -> dict:
    response = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"company_id": company_id, "title": title},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_application(
    client: TestClient,
    headers: dict[str, str],
    job_id: int,
    **overrides,
) -> dict:
    payload = {
        "job_id": job_id,
        "status": "saved",
        "priority": 3,
        "deadline": (date.today() + timedelta(days=14)).isoformat(),
        "next_action_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "notes": "Prepare application",
        **overrides,
    }
    response = client.post("/api/v1/applications", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_job_for_user(
    client: TestClient,
    headers: dict[str, str],
    suffix: str,
) -> tuple[dict, dict]:
    company = create_company(client, headers, f"Company {suffix}")
    job = create_job(client, headers, company["id"], f"Job {suffix}")
    return company, job


def test_application_endpoints_require_authentication(client: TestClient):
    assert client.get("/api/v1/applications").status_code == 401
    assert (
        client.post(
            "/api/v1/applications",
            json={"job_id": 1},
        ).status_code
        == 401
    )


def test_create_application_binds_owner_and_validates_job_ownership(
    client: TestClient,
    db_session: Session,
    user: User,
    second_user: User,
    auth_headers: dict[str, str],
):
    _, own_job = create_job_for_user(client, auth_headers, "Own")
    _, other_job = create_job_for_user(
        client,
        headers_for(second_user),
        "Other",
    )

    rejected = client.post(
        "/api/v1/applications",
        headers=auth_headers,
        json={"job_id": other_job["id"]},
    )
    assert rejected.status_code == 404
    assert rejected.json() == {"detail": "Job not found"}

    injected = client.post(
        "/api/v1/applications",
        headers=auth_headers,
        json={"job_id": own_job["id"], "owner_id": second_user.id},
    )
    assert injected.status_code == 422

    created = create_application(client, auth_headers, own_job["id"])
    application = db_session.get(Application, created["id"])
    assert "owner_id" not in created
    assert application is not None
    assert application.owner_id == user.id


def test_duplicate_application_returns_conflict(
    client: TestClient,
    auth_headers: dict[str, str],
):
    _, job = create_job_for_user(client, auth_headers, "Duplicate")
    create_application(client, auth_headers, job["id"])

    duplicate = client.post(
        "/api/v1/applications",
        headers=auth_headers,
        json={"job_id": job["id"]},
    )

    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": APPLICATION_CONFLICT}


def test_create_applied_application_defaults_applied_date(
    client: TestClient,
    auth_headers: dict[str, str],
):
    _, job = create_job_for_user(client, auth_headers, "Applied")

    created = create_application(
        client,
        auth_headers,
        job["id"],
        status="applied",
    )

    assert created["status"] == "applied"
    assert created["applied_at"] == datetime.now(UTC).date().isoformat()


def test_applied_date_invariants_are_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
):
    _, first_job = create_job_for_user(client, auth_headers, "Past Deadline")
    expired = client.post(
        "/api/v1/applications",
        headers=auth_headers,
        json={
            "job_id": first_job["id"],
            "status": "applied",
            "deadline": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert expired.status_code == 409
    assert expired.json() == {"detail": INVALID_APPLICATION_DATES}

    _, second_job = create_job_for_user(client, auth_headers, "Clear Applied Date")
    application = create_application(
        client,
        auth_headers,
        second_job["id"],
        status="applied",
    )
    cleared = client.patch(
        f"/api/v1/applications/{application['id']}",
        headers=auth_headers,
        json={"applied_at": None},
    )
    assert cleared.status_code == 409

    _, third_job = create_job_for_user(client, auth_headers, "Expired Draft")
    draft = create_application(
        client,
        auth_headers,
        third_job["id"],
        deadline=(date.today() - timedelta(days=1)).isoformat(),
    )
    transition = client.patch(
        f"/api/v1/applications/{draft['id']}/status",
        headers=auth_headers,
        json={"status": "applied"},
    )
    assert transition.status_code == 409
    assert transition.json() == {"detail": INVALID_APPLICATION_DATES}
    assert (
        client.get(
            f"/api/v1/applications/{draft['id']}/history",
            headers=auth_headers,
        ).json()
        == []
    )


def test_application_metadata_crud_cannot_change_status(
    client: TestClient,
    auth_headers: dict[str, str],
):
    _, job = create_job_for_user(client, auth_headers, "CRUD")
    created = create_application(client, auth_headers, job["id"])
    path = f"/api/v1/applications/{created['id']}"

    invalid_status_patch = client.patch(
        path,
        headers=auth_headers,
        json={"status": "offer"},
    )
    assert invalid_status_patch.status_code == 422

    updated = client.patch(
        path,
        headers=auth_headers,
        json={"priority": 5, "deadline": None, "notes": "  Updated  "},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "saved"
    assert updated.json()["priority"] == 5
    assert updated.json()["deadline"] is None
    assert updated.json()["notes"] == "Updated"

    assert client.get(path, headers=auth_headers).status_code == 200
    deleted = client.delete(path, headers=auth_headers)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(path, headers=auth_headers).status_code == 404


def test_application_ownership_covers_resource_status_and_history(
    client: TestClient,
    second_user: User,
    auth_headers: dict[str, str],
):
    other_headers = headers_for(second_user)
    _, job = create_job_for_user(client, other_headers, "Private")
    application = create_application(client, other_headers, job["id"])
    path = f"/api/v1/applications/{application['id']}"

    responses = (
        client.get(path, headers=auth_headers),
        client.patch(path, headers=auth_headers, json={"priority": 4}),
        client.patch(
            f"{path}/status",
            headers=auth_headers,
            json={"status": "applied"},
        ),
        client.get(f"{path}/history", headers=auth_headers),
        client.delete(path, headers=auth_headers),
    )
    for response in responses:
        assert response.status_code == 404
        assert response.json() == {"detail": "Application not found"}

    assert client.get(path, headers=other_headers).status_code == 200


def test_status_machine_records_ordered_history_and_applied_date(
    client: TestClient,
    auth_headers: dict[str, str],
):
    _, job = create_job_for_user(client, auth_headers, "State Machine")
    application = create_application(client, auth_headers, job["id"])
    path = f"/api/v1/applications/{application['id']}"
    transitions = ["applied", "screening", "interview", "offer", "archived"]

    for target in transitions:
        response = client.patch(
            f"{path}/status",
            headers=auth_headers,
            json={"status": target},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == target

    assert response.json()["applied_at"] == datetime.now(UTC).date().isoformat()
    history = client.get(f"{path}/history", headers=auth_headers)
    assert history.status_code == 200
    assert [(item["from_status"], item["to_status"]) for item in history.json()] == [
        ("saved", "applied"),
        ("applied", "screening"),
        ("screening", "interview"),
        ("interview", "offer"),
        ("offer", "archived"),
    ]


def test_invalid_status_transition_returns_conflict_without_history(
    client: TestClient,
    auth_headers: dict[str, str],
):
    _, job = create_job_for_user(client, auth_headers, "Invalid State")
    application = create_application(client, auth_headers, job["id"])
    path = f"/api/v1/applications/{application['id']}"

    invalid = client.patch(
        f"{path}/status",
        headers=auth_headers,
        json={"status": "offer"},
    )

    assert invalid.status_code == 409
    assert invalid.json() == {"detail": INVALID_STATUS_TRANSITION}
    assert client.get(f"{path}/history", headers=auth_headers).json() == []
    assert client.get(path, headers=auth_headers).json()["status"] == "saved"


def test_concurrent_status_updates_are_serialized_by_row_lock(
    client: TestClient,
    user: User,
    auth_headers: dict[str, str],
):
    _, job = create_job_for_user(client, auth_headers, "Concurrent State")
    application = create_application(client, auth_headers, job["id"])
    barrier = Barrier(2)

    def transition() -> str:
        with SessionLocal() as db:
            service = ApplicationService(db)
            barrier.wait(timeout=5)
            try:
                service.change_status(
                    user.id,
                    application["id"],
                    ApplicationStatus.APPLIED,
                )
            except ResourceConflictError:
                return "conflict"
            return "success"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(lambda _: transition(), range(2)))

    assert outcomes == ["conflict", "success"]
    history = client.get(
        f"/api/v1/applications/{application['id']}/history",
        headers=auth_headers,
    )
    assert [(item["from_status"], item["to_status"]) for item in history.json()] == [
        ("saved", "applied")
    ]


@pytest.mark.parametrize("terminal_status", ["rejected", "withdrawn"])
def test_terminal_status_can_be_archived(
    client: TestClient,
    auth_headers: dict[str, str],
    terminal_status: str,
):
    _, job = create_job_for_user(client, auth_headers, terminal_status)
    application = create_application(
        client,
        auth_headers,
        job["id"],
        status="applied",
    )
    path = f"/api/v1/applications/{application['id']}/status"

    assert (
        client.patch(
            path,
            headers=auth_headers,
            json={"status": terminal_status},
        ).status_code
        == 200
    )
    archived = client.patch(
        path,
        headers=auth_headers,
        json={"status": "archived"},
    )
    assert archived.status_code == 200


def test_list_applications_is_scoped_filterable_and_sorted(
    client: TestClient,
    second_user: User,
    auth_headers: dict[str, str],
):
    company, first_job = create_job_for_user(client, auth_headers, "First")
    second_job = create_job(client, auth_headers, company["id"], "Second Job")
    first = create_application(
        client,
        auth_headers,
        first_job["id"],
        status="applied",
        priority=4,
        applied_at="2026-09-01",
        next_action_at="2026-09-25T10:00:00+08:00",
    )
    second = create_application(
        client,
        auth_headers,
        second_job["id"],
        status="applied",
        priority=5,
        applied_at="2026-09-10",
        next_action_at="2026-10-01T10:00:00+08:00",
    )
    _, other_job = create_job_for_user(
        client,
        headers_for(second_user),
        "Other Filter",
    )
    create_application(client, headers_for(second_user), other_job["id"])

    response = client.get(
        "/api/v1/applications",
        headers=auth_headers,
        params={
            "company_id": company["id"],
            "status": "applied",
            "applied_from": "2026-09-01",
            "applied_to": "2026-09-30",
            "next_action_before": "2026-09-30T00:00:00Z",
            "sort_by": "priority",
            "sort_order": "desc",
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [item["id"] for item in response.json()["items"]] == [first["id"]]

    priority = client.get(
        "/api/v1/applications",
        headers=auth_headers,
        params={"priority": 5},
    )
    assert [item["id"] for item in priority.json()["items"]] == [second["id"]]

    invalid_sort = client.get(
        "/api/v1/applications",
        headers=auth_headers,
        params={"sort_by": "owner_id"},
    )
    assert invalid_sort.status_code == 422

    naive_time = client.get(
        "/api/v1/applications",
        headers=auth_headers,
        params={"next_action_before": "2026-09-30T00:00:00"},
    )
    assert naive_time.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"priority": 0},
        {"priority": 6},
        {"status": "offer"},
        {"status": "saved", "applied_at": "2026-09-01"},
        {"next_action_at": "2026-09-25T10:00:00"},
        {"applied_at": "2026-09-10", "deadline": "2026-09-01"},
        {"notes": "x" * 10001},
    ],
)
def test_application_input_validation(
    client: TestClient,
    auth_headers: dict[str, str],
    payload: dict,
):
    _, job = create_job_for_user(client, auth_headers, "Validation")
    response = client.post(
        "/api/v1/applications",
        headers=auth_headers,
        json={"job_id": job["id"], **payload},
    )
    assert response.status_code == 422


def test_job_with_application_cannot_be_deleted(
    client: TestClient,
    auth_headers: dict[str, str],
):
    _, job = create_job_for_user(client, auth_headers, "Delete Constraint")
    application = create_application(client, auth_headers, job["id"])

    conflict = client.delete(f"/api/v1/jobs/{job['id']}", headers=auth_headers)
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": JOB_HAS_APPLICATIONS}

    assert (
        client.delete(
            f"/api/v1/applications/{application['id']}",
            headers=auth_headers,
        ).status_code
        == 204
    )
    assert (
        client.delete(f"/api/v1/jobs/{job['id']}", headers=auth_headers).status_code
        == 204
    )


def test_status_history_failure_rolls_back_application_change():
    db = MagicMock()
    service = ApplicationService(db)
    service.repository = MagicMock()
    application = Application(id=1, owner_id=1, job_id=1, status="saved")
    service.repository.get_owned_for_update.return_value = application
    service.repository.add_history.side_effect = RuntimeError("history unavailable")

    with pytest.raises(RuntimeError, match="history unavailable"):
        service.change_status(1, 1, ApplicationStatus.APPLIED)

    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_application_service_maps_database_conflict_and_rolls_back():
    db = MagicMock()
    db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    service = ApplicationService(db)
    service.repository = MagicMock()
    service.job_repository = MagicMock()
    service.job_repository.get_owned.return_value = object()
    service.repository.get_by_job.return_value = None

    with pytest.raises(ResourceConflictError, match=APPLICATION_CONFLICT):
        service.create(1, ApplicationCreate(job_id=1))

    db.rollback.assert_called_once_with()


def test_deleting_application_cascades_status_history(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
):
    _, job = create_job_for_user(client, auth_headers, "History Cascade")
    application = create_application(client, auth_headers, job["id"])
    path = f"/api/v1/applications/{application['id']}"
    assert (
        client.patch(
            f"{path}/status",
            headers=auth_headers,
            json={"status": "applied"},
        ).status_code
        == 200
    )

    assert db_session.query(ApplicationStatusHistory).count() == 1
    assert client.delete(path, headers=auth_headers).status_code == 204
    db_session.expire_all()
    assert db_session.query(ApplicationStatusHistory).count() == 0
