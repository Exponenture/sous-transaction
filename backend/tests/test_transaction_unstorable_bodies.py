"""AM8: reject unfaithful bodies before categorisation or replay; small synthetic inputs."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db
URL = "/api/transactions/"


def nested_value(depth, container):
    """Top-level request is level 1; its extra container starts at level 2."""
    value = "leaf"
    for index in range(depth - 1):
        is_object = container == "object" or (container == "mixed" and index % 2 == 0)
        value = {"nested": value} if is_object else [value]
    return value


def assert_rejected_without_storage(auth_client, payload, settings):
    settings.ANTHROPIC_API_KEY = "test-key-not-a-secret"
    with patch("transactions.categorisation.anthropic.Anthropic") as provider:
        response = auth_client.post(URL, payload, format="json")
    assert response.status_code == 400, response.content
    error = response.json()["error"]
    assert set(error) == {"code", "message", "details"}
    assert error["code"] == "validation_error"
    provider.assert_not_called()
    assert auth_client.get(URL, {"status": "all"}).json()["count"] == 0


@pytest.mark.parametrize(
    "extra",
    [
        {"extra\u0000": 1, "extra\ufffd": 2},
        {"extra\ufffd": 2, "extra\u0000": 1},
        {"extra": {"key\u0000": 1, "key\ufffd": 2}},
        {"extra": [{"key\u0000": 1, "key\ufffd": 2}]},
    ],
)
def test_sanitised_key_collision_is_rejected_at_any_depth(
    auth_client, transaction_payload, settings, extra
):
    assert_rejected_without_storage(auth_client, {**transaction_payload, **extra}, settings)


@pytest.mark.parametrize("container", ["object", "array", "mixed"])
def test_depth_32_is_accepted_and_preserved(auth_client, transaction_payload, container):
    payload = {**transaction_payload, "extra": nested_value(32, container)}
    response = auth_client.post(URL, payload, format="json")
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == "categorised"
    detail = auth_client.get(f"{URL}{body['id']}/")
    assert detail.json()["raw_payload"] == payload
    replay = auth_client.post(URL, payload, format="json")
    assert replay.status_code == 200
    assert replay.json() == body


@pytest.mark.parametrize("container", ["object", "array", "mixed"])
def test_depth_33_is_rejected_without_ai_or_storage(
    auth_client, transaction_payload, settings, container
):
    assert_rejected_without_storage(
        auth_client, {**transaction_payload, "extra": nested_value(33, container)}, settings
    )


def test_deep_body_returns_400_instead_of_recursion_error(
    auth_client, transaction_payload, settings
):
    # One ~7 KB payload reproduces R11; no external dataset or large row count.
    assert_rejected_without_storage(
        auth_client, {**transaction_payload, "extra": nested_value(600, "object")}, settings
    )


def test_identical_sanitised_keys_in_different_objects_do_not_collide(
    auth_client, transaction_payload
):
    payload = {**transaction_payload, "extra": [{"key\u0000": 1}, {"key\ufffd": 2}]}
    response = auth_client.post(URL, payload, format="json")
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == "quarantined"
    issues = [issue for issue in body["issues"] if issue["code"] == "unsupported_character"]
    assert len(issues) == 1
    assert issues[0]["field"] == "extra"
    detail = auth_client.get(f"{URL}{body['id']}/")
    assert detail.json()["raw_payload"]["extra"] == [{"key\ufffd": 1}, {"key\ufffd": 2}]


@pytest.mark.parametrize(
    "invalid_extra",
    [
        {"key\u0000": 1, "key\ufffd": 2},
        nested_value(32, "array"),
    ],
)
def test_unstorable_body_is_rejected_before_existing_key_conflict(
    auth_client, transaction_payload, settings, invalid_extra
):
    first = auth_client.post(URL, transaction_payload, format="json")
    assert first.status_code == 201
    # The extra wrapper makes the array case level 33.
    extra = invalid_extra if isinstance(invalid_extra, dict) else {"nested": invalid_extra}
    settings.ANTHROPIC_API_KEY = "test-key-not-a-secret"
    with patch("transactions.categorisation.anthropic.Anthropic") as provider:
        response = auth_client.post(URL, {**transaction_payload, "extra": extra}, format="json")
    assert response.status_code == 400, response.content
    assert response.json()["error"]["code"] == "validation_error"
    provider.assert_not_called()
    assert auth_client.get(URL, {"status": "all"}).json()["count"] == 1
    detail = auth_client.get(f"{URL}{first.json()['id']}/")
    assert detail.json()["raw_payload"] == transaction_payload


def test_unstorable_body_is_rejected_before_field_validation(auth_client, settings):
    # Even without required fields, AM8 rejects rather than creating a quarantined row.
    assert_rejected_without_storage(auth_client, {"key\u0000": 1, "key\ufffd": 2}, settings)
