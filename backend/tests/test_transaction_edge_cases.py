"""Additional Lead-approved contracts in NOTES.md amendments AM1–AM5."""

import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db
URL = "/api/transactions/"
CATEGORIES = (
    "Groceries",
    "Dining Out",
    "Utilities",
    "Transportation",
    "Entertainment",
    "Healthcare",
    "Shopping",
    "Housing",
    "Education",
    "Miscellaneous",
)
RULES = [
    ("Albert Heijn Purchase", "Groceries"),
    ("AH Online Groceries", "Groceries"),
    ("NS Train Ticket", "Transportation"),
    ("Car Lease Payment", "Transportation"),
    ("Eneco Energy Bill", "Utilities"),
    ("Payment to Ziggo", "Utilities"),
    ("T-Mobile Bill Payment", "Utilities"),
    ("Municipal Tax Payment", "Utilities"),
    ("Netflix Subscription", "Entertainment"),
    ("Bol.com Purchase", "Shopping"),
    ("Rent Payment", "Housing"),
    *[
        (description, "Miscellaneous")
        for description in (
            "Tax Refund",
            "Salary from Employer",
            "Transfer to ING Account",
            "Bunq Transfer",
            "PayPal Transfer",
            "Payment to Rabobank",
            "Payment to Credit Card",
            "iDEAL Payment",
            "Geldmaat ATM Withdrawal",
            "Unrecognised merchant zxqv",
        )
    ],
]


@pytest.fixture
def anthropic_client(settings):
    settings.ANTHROPIC_API_KEY = "test-key-not-a-secret"
    # AM1 explicitly defines this seam; missing module is an intentional TDD failure.
    with patch("transactions.categorisation.anthropic.Anthropic") as constructor:
        yield constructor, constructor.return_value


def response_for(category):
    return SimpleNamespace(
        content=[
            SimpleNamespace(
                type="text",
                text=json.dumps(
                    {
                        "category": category,
                    }
                ),
            )
        ]
    )


@pytest.mark.parametrize("description,category", RULES)
@pytest.mark.parametrize("uppercase", [False, True])
def test_approved_rules_examples_are_case_insensitive(submit, description, category, uppercase):
    body = submit(description=description.upper() if uppercase else description)
    assert body["category"] == category
    assert body["categorisation_source"] == "rules"


@pytest.mark.parametrize("category", CATEGORIES)
def test_llm_accepts_each_allowed_category_once(submit, anthropic_client, category):
    constructor, client = anthropic_client
    client.messages.create.return_value = response_for(category)
    body = submit()
    assert body["category"] == category
    assert body["categorisation_source"] == "llm"
    assert body["status"] == "categorised"
    assert body["issues"] == []
    constructor.assert_called_once_with(api_key="test-key-not-a-secret", timeout=5, max_retries=0)
    client.messages.create.assert_called_once()


@pytest.mark.parametrize("failure", ["off-list", "malformed", "empty", "timeout", "exception"])
def test_llm_failure_falls_back_without_retries(submit, anthropic_client, failure):
    _, client = anthropic_client
    if failure == "off-list":
        client.messages.create.return_value = response_for("Not a category")
    elif failure == "malformed":
        client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="not JSON")]
        )
    elif failure == "empty":
        client.messages.create.return_value = SimpleNamespace(content=[])
    else:
        client.messages.create.side_effect = (
            TimeoutError("provider timeout")
            if failure == "timeout"
            else RuntimeError("provider error")
        )
    body = submit()
    assert body["category"] == "Miscellaneous"
    assert body["categorisation_source"] == "rules"
    assert body["status"] == "categorised"
    warnings = [issue for issue in body["issues"] if issue["code"] == "categorisation_fallback"]
    assert len(warnings) == 1
    assert warnings[0]["severity"] == "warning"
    assert warnings[0]["field"] is None
    client.messages.create.assert_called_once()


def test_no_api_key_never_constructs_provider(submit):
    with patch("transactions.categorisation.anthropic.Anthropic") as constructor:
        body = submit()
    constructor.assert_not_called()
    assert body["categorisation_source"] == "rules"
    assert any(issue["code"] == "categorisation_fallback" for issue in body["issues"])


def test_provider_receives_transaction_context_without_account_or_owner(
    submit, anthropic_client, transaction_payload
):
    _, client = anthropic_client
    client.messages.create.return_value = response_for("Shopping")
    submit(owner="private-owner-marker", transaction_id="private-bank-reference")
    outbound = str(client.messages.create.call_args)
    assert transaction_payload["description"] in outbound
    assert "12.5" in outbound
    assert "debit" in outbound
    assert transaction_payload["account_number"] not in outbound
    assert "private-owner-marker" not in outbound
    assert "private-bank-reference" not in outbound


def test_replay_never_calls_llm_again(auth_client, transaction_payload, anthropic_client):
    _, client = anthropic_client
    client.messages.create.return_value = response_for("Shopping")
    first = auth_client.post(URL, transaction_payload, format="json")
    assert first.status_code == 201
    replay = auth_client.post(URL, transaction_payload, format="json")
    assert replay.status_code == 200
    assert replay.json() == first.json()
    client.messages.create.assert_called_once()


@pytest.mark.parametrize("minutes,status", [(4, "categorised"), (6, "quarantined")])
def test_future_boundary_relative_to_current_time(submit, minutes, status):
    body = submit(timestamp=(timezone.now() + timedelta(minutes=minutes)).isoformat())
    assert body["status"] == status
    assert any(issue["code"] == "future_timestamp" for issue in body["issues"]) == (minutes == 6)


def test_malformed_json_returns_400_and_stores_nothing(auth_client):
    response = auth_client.post(URL, '{"amount":', content_type="application/json")
    assert response.status_code == 400, response.content
    assert set(response.json()["error"]) == {"code", "message", "details"}
    assert auth_client.get(URL, {"status": "all"}).json()["count"] == 0


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_collection_does_not_allow_mutations(auth_client, method):
    response = getattr(auth_client, method)(URL, {}, format="json")
    assert response.status_code == 405, response.content


@pytest.mark.parametrize("dirty", [False, True])
def test_account_number_never_appears_in_logs(submit, caplog, dirty):
    with caplog.at_level("DEBUG"):
        submit(account_number="NL91ABNA0417164300", amount="NaN" if dirty else "-12.50")
    assert "NL91ABNA0417164300" not in caplog.text


def test_replay_ignores_json_key_order(auth_client, transaction_payload):
    first = auth_client.post(URL, transaction_payload, format="json")
    assert first.status_code == 201
    reordered = dict(reversed(list(transaction_payload.items())))
    replay = auth_client.post(URL, reordered, format="json")
    assert replay.status_code == 200
    assert replay.json() == first.json()


def test_equivalent_json_numbers_replay(auth_client, transaction_payload):
    payload = {**transaction_payload, "amount": -12.5}
    first = auth_client.post(URL, json.dumps(payload), content_type="application/json")
    assert first.status_code == 201
    encoded = json.dumps(payload).replace('"amount": -12.5', '"amount": -12.50')
    replay = auth_client.post(URL, encoded, content_type="application/json")
    assert replay.status_code == 200
    assert replay.json() == first.json()


def test_string_and_numeric_amounts_conflict(auth_client, transaction_payload):
    first = auth_client.post(URL, transaction_payload, format="json")
    assert first.status_code == 201
    conflict = auth_client.post(URL, {**transaction_payload, "amount": -12.5}, format="json")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize("description", ["zxqvNetflixzxqv", "zxqvRentzxqv"])
def test_rule_keywords_embedded_inside_words_do_not_match(submit, description):
    assert submit(description=description)["category"] == "Miscellaneous"


def test_llm_categorises_usable_description_on_quarantined_row(submit, anthropic_client):
    _, client = anthropic_client
    client.messages.create.return_value = response_for("Shopping")
    body = submit(amount="12.50", transaction_type="debit")
    assert body["status"] == "quarantined"
    assert body["category"] == "Shopping"
    assert body["categorisation_source"] == "llm"
    client.messages.create.assert_called_once()


def test_unusable_description_never_calls_llm(submit, anthropic_client):
    constructor, client = anthropic_client
    body = submit(description="   ")
    assert body["category"] is None
    assert body["categorisation_source"] == "none"
    constructor.assert_not_called()
    client.messages.create.assert_not_called()
