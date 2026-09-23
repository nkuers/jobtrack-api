from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.exceptions.domain import ResourceConflictError
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate
from app.services.company_service import COMPANY_NAME_CONFLICT, CompanyService


def headers_for(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.username})
    return {"Authorization": f"Bearer {token}"}


def create_company(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str,
    **overrides,
):
    payload = {
        "name": name,
        "website": "https://example.com/careers",
        "industry": "Technology",
        "location": "Shanghai",
        "notes": "Target company",
        **overrides,
    }
    response = client.post("/api/v1/companies", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_company_endpoints_require_authentication(client: TestClient):
    assert client.get("/api/v1/companies").status_code == 401
    assert client.post("/api/v1/companies", json={"name": "Acme"}).status_code == 401


def test_create_company_binds_owner_and_never_accepts_owner_id(
    client: TestClient,
    db_session: Session,
    user: User,
    second_user: User,
    auth_headers: dict[str, str],
):
    rejected = client.post(
        "/api/v1/companies",
        headers=auth_headers,
        json={"name": "Injected", "owner_id": second_user.id},
    )
    assert rejected.status_code == 422

    created = create_company(client, auth_headers, name="  Acme  ")
    company = db_session.get(Company, created["id"])

    assert created["name"] == "Acme"
    assert "owner_id" not in created
    assert company is not None
    assert company.owner_id == user.id
    assert db_session.query(Company).count() == 1


def test_company_crud_and_partial_update(
    client: TestClient,
    auth_headers: dict[str, str],
):
    created = create_company(client, auth_headers, name="Acme")

    fetched = client.get(
        f"/api/v1/companies/{created['id']}",
        headers=auth_headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["website"] == "https://example.com/careers"

    updated = client.patch(
        f"/api/v1/companies/{created['id']}",
        headers=auth_headers,
        json={"location": "  Beijing  ", "notes": None},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Acme"
    assert updated.json()["location"] == "Beijing"
    assert updated.json()["notes"] is None

    deleted = client.delete(
        f"/api/v1/companies/{created['id']}",
        headers=auth_headers,
    )
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert (
        client.get(
            f"/api/v1/companies/{created['id']}",
            headers=auth_headers,
        ).status_code
        == 404
    )


def test_company_ownership_is_enforced_for_every_resource_operation(
    client: TestClient,
    second_user: User,
    auth_headers: dict[str, str],
):
    other_company = create_company(
        client,
        headers_for(second_user),
        name="Other User Company",
    )
    path = f"/api/v1/companies/{other_company['id']}"

    get_response = client.get(path, headers=auth_headers)
    patch_response = client.patch(
        path,
        headers=auth_headers,
        json={"name": "Stolen"},
    )
    delete_response = client.delete(path, headers=auth_headers)

    for response in (get_response, patch_response, delete_response):
        assert response.status_code == 404
        assert response.json() == {"detail": "Company not found"}

    missing = client.get("/api/v1/companies/2147483647", headers=auth_headers)
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Company not found"}
    assert client.get(path, headers=headers_for(second_user)).status_code == 200


def test_list_companies_is_owner_scoped_filterable_and_paginated(
    client: TestClient,
    second_user: User,
    auth_headers: dict[str, str],
):
    create_company(
        client,
        auth_headers,
        name="Alpha Labs",
        industry="Technology",
        location="Shanghai",
    )
    create_company(
        client,
        auth_headers,
        name="Beta Bank",
        industry="Finance",
        location="Beijing",
    )
    create_company(
        client,
        auth_headers,
        name="Gamma Tech",
        industry="Technology",
        location="Shenzhen",
    )
    create_company(client, headers_for(second_user), name="Other Alpha")

    filtered = client.get(
        "/api/v1/companies",
        headers=auth_headers,
        params={"industry": "technology", "keyword": "a", "page_size": 1},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 2
    assert filtered.json()["page"] == 1
    assert filtered.json()["page_size"] == 1
    assert len(filtered.json()["items"]) == 1

    second_page = client.get(
        "/api/v1/companies",
        headers=auth_headers,
        params={"industry": "technology", "page": 2, "page_size": 1},
    )
    assert second_page.status_code == 200
    assert second_page.json()["total"] == 2
    assert len(second_page.json()["items"]) == 1
    assert second_page.json()["items"] != filtered.json()["items"]

    location = client.get(
        "/api/v1/companies",
        headers=auth_headers,
        params={"location": "jing"},
    )
    assert [item["name"] for item in location.json()["items"]] == ["Beta Bank"]

    invalid_page_size = client.get(
        "/api/v1/companies",
        headers=auth_headers,
        params={"page_size": 101},
    )
    assert invalid_page_size.status_code == 422


def test_company_name_conflict_is_per_owner_and_case_insensitive(
    client: TestClient,
    second_user: User,
    auth_headers: dict[str, str],
):
    create_company(client, auth_headers, name="Acme")

    duplicate = client.post(
        "/api/v1/companies",
        headers=auth_headers,
        json={"name": "  ACME "},
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": COMPANY_NAME_CONFLICT}

    other_owner = client.post(
        "/api/v1/companies",
        headers=headers_for(second_user),
        json={"name": "ACME"},
    )
    assert other_owner.status_code == 201


def test_company_update_rejects_duplicate_name(
    client: TestClient,
    auth_headers: dict[str, str],
):
    create_company(client, auth_headers, name="Acme")
    beta = create_company(client, auth_headers, name="Beta")

    duplicate = client.patch(
        f"/api/v1/companies/{beta['id']}",
        headers=auth_headers,
        json={"name": " acME "},
    )

    assert duplicate.status_code == 409
    unchanged = client.get(
        f"/api/v1/companies/{beta['id']}",
        headers=auth_headers,
    )
    assert unchanged.json()["name"] == "Beta"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "   "},
        {"name": "x" * 121},
        {"name": "Acme", "website": "not-a-url"},
        {"name": "Acme", "industry": "x" * 101},
        {"name": "Acme", "location": "x" * 256},
        {"name": "Acme", "notes": "x" * 5001},
    ],
)
def test_company_input_validation(
    client: TestClient,
    auth_headers: dict[str, str],
    payload: dict[str, str],
):
    response = client.post(
        "/api/v1/companies",
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == 422


def test_company_update_rejects_null_name(
    client: TestClient,
    auth_headers: dict[str, str],
):
    company = create_company(client, auth_headers, name="Acme")

    response = client.patch(
        f"/api/v1/companies/{company['id']}",
        headers=auth_headers,
        json={"name": None},
    )

    assert response.status_code == 422


def test_company_service_rolls_back_when_commit_fails():
    db = MagicMock()
    db.commit.side_effect = RuntimeError("database unavailable")
    service = CompanyService(db)
    service.repository = MagicMock()
    service.repository.get_by_normalized_name.return_value = None

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.create(1, CompanyCreate(name="Acme"))

    db.rollback.assert_called_once_with()
    db.refresh.assert_not_called()


def test_company_service_maps_database_conflict_and_rolls_back():
    db = MagicMock()
    db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    service = CompanyService(db)
    service.repository = MagicMock()
    service.repository.get_by_normalized_name.return_value = None

    with pytest.raises(ResourceConflictError, match=COMPANY_NAME_CONFLICT):
        service.create(1, CompanyCreate(name="Acme"))

    db.rollback.assert_called_once_with()
