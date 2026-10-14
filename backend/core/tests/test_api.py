import pytest

pytestmark = pytest.mark.django_db


def test_health_is_public_and_checks_db(api_client):
    res = api_client.get("/api/health/", HTTP_X_REQUEST_ID="abc-123")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "db": "ok"}
    assert res["X-Request-ID"] == "abc-123"


def test_validation_error_shape(api_client):
    res = api_client.post("/api/auth/token/", {})
    assert res.status_code == 400
    err = res.json()["error"]
    assert err["code"] == "validation_error"
    assert {"username", "password"} <= err["details"].keys()
