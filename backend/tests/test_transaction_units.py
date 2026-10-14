"""Pure-function contracts from NOTES.md: no HTTP, database marker or AI calls."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from transactions.categorisation import by_rules
from transactions.services import same_json
from transactions.validation import validate

NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)


def test_validation_normalises_clean_input_without_mutating_it(transaction_payload):
    payload = {
        **transaction_payload,
        "amount": " -12.50 ",
        "transaction_type": " DEBIT ",
        "account_number": " nl91 abna 0417 1643 00 ",
        "currency": " eur ",
    }
    original = payload.copy()
    result = validate(payload, now=NOW)
    assert result.issues == []
    assert result.values["amount"] == Decimal("-12.50")
    assert result.values["currency"] == "EUR"
    assert result.values["transaction_type"] == "debit"
    assert result.values["account_number"] == "NL91ABNA0417164300"
    assert payload == original


@pytest.mark.parametrize("amount", ["NaN", "-1.234", "1e1000000"])
def test_validation_flags_invalid_amounts_without_raising(transaction_payload, amount):
    result = validate({**transaction_payload, "amount": amount}, now=NOW)
    assert result.values["amount"] is None
    assert any(issue["code"] == "invalid_amount" for issue in result.issues)


def test_validation_accumulates_errors_and_retains_valid_fields(transaction_payload):
    result = validate({**transaction_payload, "amount": True, "timestamp": "bad"}, now=NOW)
    assert {(issue["code"], issue["field"]) for issue in result.issues} == {
        ("invalid_amount", "amount"),
        ("invalid_timestamp", "timestamp"),
    }
    assert result.values["description"] == transaction_payload["description"]
    assert result.values["transaction_type"] == "debit"


@pytest.mark.parametrize("minutes,blocked", [(4, False), (6, True)])
def test_validation_uses_supplied_time_for_future_boundary(transaction_payload, minutes, blocked):
    result = validate(
        {
            **transaction_payload,
            "timestamp": (NOW + timedelta(minutes=minutes)).isoformat(),
        },
        now=NOW,
    )
    assert any(issue["code"] == "future_timestamp" for issue in result.issues) == blocked


@pytest.mark.parametrize(
    "timestamp,code,expected",
    [
        ("2024-03-31 02:30:00", "nonexistent_local_time", None),
        ("2024-10-27 02:30:00", "ambiguous_local_time", "2024-10-27T00:30:00+00:00"),
    ],
)
def test_validation_handles_amsterdam_dst(transaction_payload, timestamp, code, expected):
    result = validate({**transaction_payload, "timestamp": timestamp}, now=NOW)
    issue = next(issue for issue in result.issues if issue["code"] == code)
    assert issue["severity"] == ("blocking" if expected is None else "warning")
    if expected is None:
        assert result.values["timestamp"] is None
    else:
        assert result.values["timestamp"].astimezone(timezone.utc) == datetime.fromisoformat(
            expected
        )


@pytest.mark.parametrize(
    "description,category",
    [
        ("Albert Heijn Purchase", "Groceries"),
        ("Payment to Ziggo", "Utilities"),
        ("NS Train Ticket", "Transportation"),
        ("NETFLIX SUBSCRIPTION", "Entertainment"),
        ("Bol.com Purchase", "Shopping"),
        ("Rent Payment", "Housing"),
        ("Salary from School Employer", "Miscellaneous"),
        ("Transfer to Rent Account", "Miscellaneous"),
        ("Tax Refund Netflix", "Miscellaneous"),
        ("zxqvNetflixzxqv", "Miscellaneous"),
        ("unknown zxqv", "Miscellaneous"),
    ],
)
def test_keyword_rules_follow_approved_categories_and_precedence(description, category):
    assert by_rules(description) == category


@pytest.mark.parametrize(
    "left,right,equal",
    [
        ({"a": 1, "b": 2}, {"b": 2, "a": 1}, True),
        (12.5, 12.50, True),
        (12, 12.0, True),
        ("12.50", 12.5, False),
        (True, 1, False),
        (False, 0, False),
        (None, None, True),
        ([1, {"a": 2}], [1.0, {"a": 2.0}], True),
        ([1, 2], [2, 1], False),
        ([1], [1, 2], False),
        ({"a": 1}, {"a": 1, "extra": None}, False),
    ],
)
def test_json_equality_matches_replay_contract(left, right, equal):
    assert same_json(left, right) is equal
    assert same_json(right, left) is equal
