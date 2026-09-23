from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_placeholder_user_creation_route_is_not_registered():
    response = client.post(
        "/users/",
        json={
            "username": "houngdev",
            "password": "secret123",
        },
    )

    assert response.status_code == 404
    assert "secret123" not in response.text
