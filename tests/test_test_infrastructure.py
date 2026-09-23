from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


def test_reusable_authenticated_user_fixtures(
    client: TestClient,
    db_session: Session,
    user: User,
    second_user: User,
    auth_headers: dict[str, str],
):
    response = client.get("/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["id"] == user.id
    assert second_user.id != user.id
    assert db_session.query(User).count() == 3


def test_each_test_starts_with_only_the_admin(db_session: Session):
    users = db_session.query(User).all()

    assert [user.username for user in users] == ["houngdev"]
