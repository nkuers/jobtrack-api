from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.exceptions.domain import ResourceConflictError
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate
from app.services.company_service import COMPANY_HAS_JOBS
from app.services.job_service import JOB_CONFLICT, JobService


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
    *,
    title: str,
    **overrides,
) -> dict:
    payload = {
        "company_id": company_id,
        "title": title,
        "employment_type": "full_time",
        "work_mode": "hybrid",
        "location": "Shanghai",
        "source": "Company website",
        "url": "https://example.com/jobs/1",
        "salary_min": 2_000_000,
        "salary_max": 3_000_000,
        "salary_currency": "cny",
        "description": "Backend role",
        "status": "open",
        **overrides,
    }
    response = client.post("/api/v1/jobs", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_job_endpoints_require_authentication(client: TestClient):
    assert client.get("/api/v1/jobs").status_code == 401
    assert (
        client.post(
            "/api/v1/jobs",
            json={"company_id": 1, "title": "Backend Engineer"},
        ).status_code
        == 401
    )


def test_create_job_binds_owner_and_validates_company_ownership(
    client: TestClient,
    db_session: Session,
    user: User,
    second_user: User,
    auth_headers: dict[str, str],
):
    own_company = create_company(client, auth_headers, "Acme")
    other_company = create_company(client, headers_for(second_user), "Other")

    rejected = client.post(
        "/api/v1/jobs",
        headers=auth_headers,
        json={"company_id": other_company["id"], "title": "Backend Engineer"},
    )
    assert rejected.status_code == 404
    assert rejected.json() == {"detail": "Company not found"}

    injected = client.post(
        "/api/v1/jobs",
        headers=auth_headers,
        json={
            "company_id": own_company["id"],
            "title": "Injected",
            "owner_id": second_user.id,
        },
    )
    assert injected.status_code == 422

    created = create_job(
        client,
        auth_headers,
        own_company["id"],
        title="  Backend Engineer  ",
    )
    job = db_session.get(Job, created["id"])
    assert created["title"] == "Backend Engineer"
    assert created["salary_currency"] == "CNY"
    assert "owner_id" not in created
    assert job is not None
    assert job.owner_id == user.id


def test_job_crud_and_partial_update(
    client: TestClient,
    auth_headers: dict[str, str],
):
    first_company = create_company(client, auth_headers, "Acme")
    second_company = create_company(client, auth_headers, "Beta")
    created = create_job(
        client,
        auth_headers,
        first_company["id"],
        title="Backend Engineer",
    )

    fetched = client.get(f"/api/v1/jobs/{created['id']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["salary_min"] == 2_000_000

    updated = client.patch(
        f"/api/v1/jobs/{created['id']}",
        headers=auth_headers,
        json={
            "company_id": second_company["id"],
            "work_mode": "remote",
            "location": None,
            "status": "paused",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Backend Engineer"
    assert updated.json()["company_id"] == second_company["id"]
    assert updated.json()["work_mode"] == "remote"
    assert updated.json()["location"] is None
    assert updated.json()["status"] == "paused"

    deleted = client.delete(f"/api/v1/jobs/{created['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert (
        client.get(f"/api/v1/jobs/{created['id']}", headers=auth_headers).status_code
        == 404
    )


def test_job_ownership_is_enforced_for_read_write_and_delete(
    client: TestClient,
    second_user: User,
    auth_headers: dict[str, str],
):
    other_headers = headers_for(second_user)
    own_company = create_company(client, auth_headers, "Own")
    company = create_company(client, other_headers, "Other")
    job = create_job(client, other_headers, company["id"], title="Private Job")
    path = f"/api/v1/jobs/{job['id']}"

    responses = (
        client.get(path, headers=auth_headers),
        client.patch(path, headers=auth_headers, json={"title": "Stolen"}),
        client.delete(path, headers=auth_headers),
    )
    for response in responses:
        assert response.status_code == 404
        assert response.json() == {"detail": "Job not found"}

    assert client.get(path, headers=other_headers).status_code == 200

    own_job = create_job(
        client,
        auth_headers,
        own_company["id"],
        title="Own Job",
    )
    move_to_other_company = client.patch(
        f"/api/v1/jobs/{own_job['id']}",
        headers=auth_headers,
        json={"company_id": company["id"]},
    )
    assert move_to_other_company.status_code == 404
    assert move_to_other_company.json() == {"detail": "Company not found"}


def test_list_jobs_is_scoped_filterable_paginated_and_safely_sorted(
    client: TestClient,
    second_user: User,
    auth_headers: dict[str, str],
):
    acme = create_company(client, auth_headers, "Acme")
    beta = create_company(client, auth_headers, "Beta")
    first = create_job(
        client,
        auth_headers,
        acme["id"],
        title="Senior Backend Engineer",
        salary_min=300,
        salary_max=400,
        work_mode="remote",
    )
    second = create_job(
        client,
        auth_headers,
        acme["id"],
        title="Junior Backend Engineer",
        salary_min=100,
        salary_max=200,
        work_mode="remote",
    )
    create_job(
        client,
        auth_headers,
        beta["id"],
        title="Data Engineer",
        salary_min=200,
        salary_max=300,
        status="closed",
        work_mode="onsite",
    )
    other_company = create_company(client, headers_for(second_user), "Other")
    create_job(
        client,
        headers_for(second_user),
        other_company["id"],
        title="Other Backend Engineer",
    )

    response = client.get(
        "/api/v1/jobs",
        headers=auth_headers,
        params={
            "company_id": acme["id"],
            "status": "open",
            "work_mode": "remote",
            "keyword": "backend",
            "sort_by": "salary_min",
            "sort_order": "asc",
            "page_size": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["id"] for item in response.json()["items"]] == [second["id"]]

    next_page = client.get(
        "/api/v1/jobs",
        headers=auth_headers,
        params={
            "company_id": acme["id"],
            "sort_by": "salary_min",
            "sort_order": "asc",
            "page": 2,
            "page_size": 1,
        },
    )
    assert [item["id"] for item in next_page.json()["items"]] == [first["id"]]

    invalid_sort = client.get(
        "/api/v1/jobs",
        headers=auth_headers,
        params={"sort_by": "owner_id"},
    )
    assert invalid_sort.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   "},
        {"title": "x" * 201},
        {"title": "Backend", "employment_type": "permanent"},
        {"title": "Backend", "work_mode": "everywhere"},
        {"title": "Backend", "status": "unknown"},
        {"title": "Backend", "url": "not-a-url"},
        {"title": "Backend", "salary_min": -1},
        {"title": "Backend", "salary_min": 200, "salary_max": 100},
        {"title": "Backend", "salary_currency": "US"},
    ],
)
def test_job_input_validation(
    client: TestClient,
    auth_headers: dict[str, str],
    payload: dict,
):
    company = create_company(client, auth_headers, "Acme")
    response = client.post(
        "/api/v1/jobs",
        headers=auth_headers,
        json={"company_id": company["id"], **payload},
    )
    assert response.status_code == 422


def test_partial_update_validates_salary_against_existing_value(
    client: TestClient,
    auth_headers: dict[str, str],
):
    company = create_company(client, auth_headers, "Acme")
    job = create_job(
        client,
        auth_headers,
        company["id"],
        title="Backend",
        salary_min=100,
        salary_max=200,
    )

    response = client.patch(
        f"/api/v1/jobs/{job['id']}",
        headers=auth_headers,
        json={"salary_min": 300},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "salary_min cannot exceed salary_max"}


def test_company_with_jobs_cannot_be_deleted(
    client: TestClient,
    auth_headers: dict[str, str],
):
    company = create_company(client, auth_headers, "Acme")
    job = create_job(client, auth_headers, company["id"], title="Backend")

    conflict = client.delete(
        f"/api/v1/companies/{company['id']}",
        headers=auth_headers,
    )
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": COMPANY_HAS_JOBS}

    assert (
        client.delete(f"/api/v1/jobs/{job['id']}", headers=auth_headers).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/v1/companies/{company['id']}",
            headers=auth_headers,
        ).status_code
        == 204
    )


def test_job_service_rolls_back_when_commit_fails():
    db = MagicMock()
    db.commit.side_effect = RuntimeError("database unavailable")
    service = JobService(db)
    service.repository = MagicMock()
    service.company_repository = MagicMock()
    service.company_repository.get_owned.return_value = object()

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.create(1, JobCreate(company_id=1, title="Backend"))

    db.rollback.assert_called_once_with()
    db.refresh.assert_not_called()


def test_job_service_maps_integrity_error_and_rolls_back():
    db = MagicMock()
    db.commit.side_effect = IntegrityError("insert", {}, Exception("constraint"))
    service = JobService(db)
    service.repository = MagicMock()
    service.company_repository = MagicMock()
    service.company_repository.get_owned.return_value = object()

    with pytest.raises(ResourceConflictError, match=JOB_CONFLICT):
        service.create(1, JobCreate(company_id=1, title="Backend"))

    db.rollback.assert_called_once_with()
