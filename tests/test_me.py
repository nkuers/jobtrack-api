from fastapi.testclient import TestClient

from app.auth.jwt import create_access_token
from app.main import app

client = TestClient(app)


def test_me():
    token = create_access_token(
        {"sub": "houngdev"},
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.json()["username"] == "houngdev"
    assert "password" not in response.json()


def test_legacy_me_route_is_not_registered():
    response = client.get("/me/")

    assert response.status_code == 404
