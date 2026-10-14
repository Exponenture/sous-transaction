"""Lightweight regressions for Lead-approved review fixes AM6 and AM7."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.apps import apps
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from core.tests.factories import UserFactory

pytestmark = pytest.mark.django_db
URL = "/api/transactions/"


@pytest.mark.parametrize("amount", ["1e1000000", "-1e1000000"])
def test_decimal_arithmetic_failure_quarantines_instead_of_returning_500(submit, amount):
    body = submit(amount=amount)
    assert body["status"] == "quarantined"
    assert body["amount"] is None
    assert any(
        issue["code"] == "invalid_amount"
        and issue["field"] == "amount"
        and issue["severity"] == "blocking"
        for issue in body["issues"]
    )


@pytest.mark.parametrize(
    "changes,sanitised,fields",
    [
        (
            {"description": "Merchant\u0000name"},
            {"description": "Merchant\ufffdname"},
            ["description"],
        ),
        (
            {"extra": {"nested": ["a\u0000b", {"key\u0000": "value\u0000"}]}},
            {"extra": {"nested": ["a\ufffdb", {"key\ufffd": "value\ufffd"}]}},
            ["extra"],
        ),
        ({"extra\u0000": "value\u0000"}, {"extra\ufffd": "value\ufffd"}, ["extra\ufffd"]),
        (
            {"description": "Merchant\u0000", "extra": ["one\u0000", "two\u0000"]},
            {"description": "Merchant\ufffd", "extra": ["one\ufffd", "two\ufffd"]},
            ["description", "extra"],
        ),
    ],
)
def test_nul_characters_are_sanitised_once_per_top_level_field_and_replay(
    auth_client, transaction_payload, changes, sanitised, fields
):
    payload = {**transaction_payload, **changes}
    first = auth_client.post(URL, payload, format="json")
    assert first.status_code == 201, first.content
    body = first.json()
    assert body["status"] == "quarantined"
    issues = [issue for issue in body["issues"] if issue["code"] == "unsupported_character"]
    assert sorted(issue["field"] for issue in issues) == sorted(fields)
    assert all(issue["severity"] == "blocking" for issue in issues)
    detail = auth_client.get(f"{URL}{body['id']}/")
    assert detail.status_code == 200
    assert detail.json()["raw_payload"] == {**transaction_payload, **sanitised}
    if "description" in sanitised:
        assert body["description"] == sanitised["description"]
    replay = auth_client.post(URL, payload, format="json")
    assert replay.status_code == 200
    assert replay.json() == body
    sanitised_replay = auth_client.post(URL, {**transaction_payload, **sanitised}, format="json")
    assert sanitised_replay.status_code == 200
    assert sanitised_replay.json() == body
    assert auth_client.get(URL, {"status": "all"}).json()["count"] == 1


@pytest.mark.parametrize(
    "description,kind",
    [
        ("Salary from School Employer", "credit"),
        ("Transfer to Rent Account", "debit"),
        ("Tax Refund Netflix", "credit"),
        ("ATM Withdrawal near Supermarket", "debit"),
        ("Credit Card Payment Amazon", "debit"),
    ],
)
def test_money_movements_take_precedence_over_spending_keywords(submit, description, kind):
    body = submit(
        description=description,
        transaction_type=kind,
        amount="12.50" if kind == "credit" else "-12.50",
    )
    assert body["status"] == "categorised"
    assert body["category"] == "Miscellaneous"
    assert body["categorisation_source"] == "rules"


def test_provider_constructor_failure_uses_rules_fallback(submit, settings):
    settings.ANTHROPIC_API_KEY = "test-key-not-a-secret"
    with patch(
        "transactions.categorisation.anthropic.Anthropic",
        side_effect=RuntimeError("client initialisation failed"),
    ) as constructor:
        body = submit()
    constructor.assert_called_once_with(api_key="test-key-not-a-secret", timeout=5, max_retries=0)
    assert body["status"] == "categorised"
    assert body["category"] == "Miscellaneous"
    assert body["categorisation_source"] == "rules"
    assert any(issue["code"] == "categorisation_fallback" for issue in body["issues"])


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("description", 123, "invalid_description"),
        ("timestamp", 1700000000, "invalid_timestamp"),
        ("amount", True, "invalid_amount"),
        ("transaction_type", ["debit"], "invalid_transaction_type"),
        ("account_number", 1234567890, "invalid_account_number"),
        ("currency", ["EUR"], "invalid_currency"),
        ("transaction_id", True, "invalid_transaction_id"),
    ],
)
def test_wrong_json_types_are_flagged_without_coercion(submit, auth_client, field, value, code):
    body = submit(**{field: value})
    assert body["status"] == "quarantined"
    assert body[field] is None
    assert any(issue["code"] == code and issue["field"] == field for issue in body["issues"])
    assert auth_client.get(f"{URL}{body['id']}/").json()["raw_payload"][field] == value


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", URL),
        ("post", URL),
        ("get", f"{URL}00000000-0000-0000-0000-000000000001/"),
    ],
)
def test_expired_access_token_is_rejected(api_client, transaction_payload, method, path):
    token = AccessToken.for_user(UserFactory())
    token.set_exp(lifetime=-timedelta(minutes=1))
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = (
        api_client.post(path, transaction_payload, format="json")
        if method == "post"
        else api_client.get(path)
    )
    assert response.status_code == 401
    assert set(response.json()["error"]) == {"code", "message", "details"}


def test_equal_timestamps_use_descending_creation_time(submit, auth_client):
    first = submit(transaction_id="first")
    second = submit(transaction_id="second")
    model = apps.get_model("transactions", "Transaction")
    now = timezone.now()
    # Explicit fixture times avoid timing races and sleeps in CI.
    model.objects.filter(pk=first["id"]).update(created_at=now - timedelta(minutes=1))
    model.objects.filter(pk=second["id"]).update(created_at=now)
    response = auth_client.get(URL)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [second["id"], first["id"]]


def test_openapi_documents_transaction_routes_and_authentication(auth_client):
    response = auth_client.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema["paths"]
    collection = paths[URL]
    detail = paths[f"{URL}{{id}}/"]
    for operation in (collection["get"], collection["post"], detail["get"]):
        assert operation.get("security", schema.get("security"))
    assert {"200", "201"} <= collection["post"]["responses"].keys()
    assert "application/json" in collection["post"]["requestBody"]["content"]
    assert "200" in detail["get"]["responses"]
    assert {"status", "category"} <= {
        parameter["name"] for parameter in collection["get"]["parameters"]
    }
