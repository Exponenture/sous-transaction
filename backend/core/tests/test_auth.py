import pytest

from core.tests.factories import UserFactory

pytestmark = pytest.mark.django_db
TOKEN = "/api/auth/token/"
REFRESH = "/api/auth/token/refresh/"


@pytest.fixture
def user():
    user = UserFactory()
    user.set_password("correct-horse")
    user.save()
    return user


def test_obtain_token_and_refresh_rotates(api_client, user):
    res = api_client.post(TOKEN, {"username": user.username, "password": "correct-horse"})
    assert res.status_code == 200, res.json()
    tokens = res.json()
    assert {"access", "refresh"} <= tokens.keys()

    # Refresh rotates: a new refresh token is issued alongside the new access token.
    res = api_client.post(REFRESH, {"refresh": tokens["refresh"]})
    assert res.status_code == 200, res.json()
    assert res.json()["refresh"] != tokens["refresh"]


def test_bad_credentials_and_bad_token_are_401(api_client, user):
    res = api_client.post(TOKEN, {"username": user.username, "password": "wrong"})
    assert res.status_code == 401
    assert "error" in res.json()

    res = api_client.post(REFRESH, {"refresh": "not-a-jwt"})
    assert res.status_code == 401
    assert "error" in res.json()
