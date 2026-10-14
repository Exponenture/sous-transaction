"""Black-box contracts from NOTES.md; no transaction implementation imports."""

from datetime import datetime
from uuid import UUID

import pytest

pytestmark = pytest.mark.django_db
URL = "/api/transactions/"
FIELDS = {
    "id",
    "transaction_id",
    "amount",
    "currency",
    "timestamp",
    "description",
    "transaction_type",
    "account_number",
    "category",
    "categorisation_source",
    "status",
    "issues",
    "created_at",
}
REQUIRED = (
    "transaction_id",
    "amount",
    "timestamp",
    "description",
    "transaction_type",
    "account_number",
)


def assert_issue(body, code, field, severity="blocking"):
    matches = [
        issue for issue in body["issues"] if issue["code"] == code and issue["field"] == field
    ]
    assert len(matches) == 1, body["issues"]
    issue = matches[0]
    assert set(issue) == {"code", "field", "severity", "message"}
    assert issue["severity"] == severity
    assert isinstance(issue["message"], str) and issue["message"]


def test_clean_transaction_is_stored_and_returned_with_documented_fields(submit, auth_client):
    body = submit()
    assert set(body) == FIELDS
    UUID(body["id"])
    assert body["amount"] == "-12.50"
    assert body["currency"] == "EUR"
    assert body["status"] == "categorised"
    assert body["category"] == "Miscellaneous"
    assert body["categorisation_source"] == "rules"
    assert all(issue["severity"] == "warning" for issue in body["issues"])
    assert any(issue["code"] == "categorisation_fallback" for issue in body["issues"])
    for field in ("timestamp", "created_at"):
        assert datetime.fromisoformat(body[field].replace("Z", "+00:00")).utcoffset() is not None
    detail = auth_client.get(f"{URL}{body['id']}/")
    assert detail.status_code == 200
    assert {key: value for key, value in detail.json().items() if key != "raw_payload"} == body


@pytest.mark.parametrize(
    "amount,expected,kind",
    [
        ("-12.50", "-12.50", "debit"),
        (-12.5, "-12.50", "debit"),
        ("1e3", "1000.00", "credit"),
        ("-999999999999.99", "-999999999999.99", "debit"),
    ],
)
def test_supported_amounts_preserve_decimal_value(submit, amount, expected, kind):
    body = submit(amount=amount, transaction_type=kind)
    assert body["amount"] == expected
    assert body["status"] == "categorised"


def test_strings_are_normalised_without_altering_raw_payload(
    submit, auth_client, transaction_payload
):
    changes = {
        "description": "  Unrecognised merchant zxqv  ",
        "transaction_type": " DEBIT ",
        "currency": " eur ",
        "account_number": " nl91 abna 0417 1643 00 ",
        "extra": {"unchanged": [1, "two"]},
    }
    body = submit(**changes)
    assert body["status"] == "categorised"
    assert body["description"] == "Unrecognised merchant zxqv"
    assert body["transaction_type"] == "debit"
    assert body["currency"] == "EUR"
    assert body["account_number"] == "NL91ABNA0417164300"
    assert auth_client.get(f"{URL}{body['id']}/").json()["raw_payload"] == {
        **transaction_payload,
        **changes,
    }


@pytest.mark.parametrize("field", REQUIRED)
@pytest.mark.parametrize("missing_kind", ["absent", "null", "blank"])
def test_missing_required_fields_are_accepted_with_blocking_issues(
    auth_client, transaction_payload, field, missing_kind
):
    payload = dict(transaction_payload)
    if missing_kind == "absent":
        payload.pop(field)
    else:
        payload[field] = None if missing_kind == "null" else "   "
    response = auth_client.post(URL, payload, format="json")
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == "quarantined"
    assert_issue(body, "missing_field", field)


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("amount", "abc", "invalid_amount"),
        ("amount", "NaN", "invalid_amount"),
        ("amount", "Infinity", "invalid_amount"),
        ("amount", "-Infinity", "invalid_amount"),
        ("amount", "-1.234", "invalid_amount"),
        ("amount", "1000000000000", "invalid_amount"),
        ("amount", "-1000000000000", "invalid_amount"),
        ("amount", "0", "zero_amount"),
        ("amount", "-0.00", "zero_amount"),
        ("timestamp", "not-a-date", "invalid_timestamp"),
        ("timestamp", "2024-02-30T12:00:00Z", "invalid_timestamp"),
        ("transaction_type", "transfer", "invalid_transaction_type"),
        ("currency", "EU", "invalid_currency"),
        ("currency", "EURO", "invalid_currency"),
        ("currency", "E1R", "invalid_currency"),
        ("account_number", "1234567890", "invalid_account_number"),
        ("account_number", "NL1234567", "invalid_account_number"),
        ("account_number", "NL" + "1" * 33, "invalid_account_number"),
        ("account_number", "NL1234!678", "invalid_account_number"),
        ("description", "x" * 256, "invalid_description"),
        ("transaction_id", "x" * 65, "invalid_transaction_id"),
        ("transaction_id", [], "invalid_transaction_id"),
        ("transaction_id", {}, "invalid_transaction_id"),
        ("transaction_id", 1.5, "invalid_transaction_id"),
    ],
)
def test_dirty_fields_are_quarantined_and_preserved_in_raw_payload(
    submit, auth_client, field, value, code
):
    body = submit(**{field: value})
    assert body["status"] == "quarantined"
    assert_issue(body, code, field)
    detail = auth_client.get(f"{URL}{body['id']}/")
    assert detail.status_code == 200
    assert detail.json()["raw_payload"][field] == value


@pytest.mark.parametrize("amount,kind", [("12.50", "debit"), ("-12.50", "credit")])
def test_sign_mismatch_keeps_parsed_fields_and_category_suggestion(submit, amount, kind):
    body = submit(amount=amount, transaction_type=kind)
    assert body["status"] == "quarantined"
    assert body["amount"] == amount
    assert body["transaction_type"] == kind
    assert body["category"] == "Miscellaneous"
    assert body["categorisation_source"] == "rules"
    assert any(issue["code"] == "sign_type_mismatch" for issue in body["issues"])


def test_all_independent_issues_accumulate_and_valid_fields_survive(submit):
    body = submit(amount="NaN", timestamp="bad", currency="123", account_number="bad")
    assert body["status"] == "quarantined"
    for code, field in [
        ("invalid_amount", "amount"),
        ("invalid_timestamp", "timestamp"),
        ("invalid_currency", "currency"),
        ("invalid_account_number", "account_number"),
    ]:
        assert_issue(body, code, field)
    assert body["amount"] is None
    assert body["timestamp"] is None
    assert body["description"] == "Unrecognised merchant zxqv"
    assert body["transaction_type"] == "debit"


def test_empty_object_records_one_missing_issue_for_every_required_field(auth_client):
    response = auth_client.post(URL, {}, format="json")
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == "quarantined"
    for field in REQUIRED:
        assert_issue(body, "missing_field", field)
    assert body["category"] is None
    assert body["categorisation_source"] == "none"


@pytest.mark.parametrize("description", [None, "", "   ", "x" * 256])
def test_unusable_description_is_not_categorised(submit, description):
    body = submit(description=description)
    assert body["status"] == "quarantined"
    assert body["category"] is None
    assert body["categorisation_source"] == "none"
    assert not any(issue["code"] == "categorisation_fallback" for issue in body["issues"])


@pytest.mark.parametrize("body", [[], [1, 2], "text", 123, None])
def test_non_object_json_is_a_validation_error(auth_client, body):
    import json

    response = auth_client.post(URL, json.dumps(body), content_type="application/json")
    assert response.status_code == 400, response.content
    error = response.json()["error"]
    assert set(error) == {"code", "message", "details"}
    assert error["code"] == "validation_error"
    assert auth_client.get(URL, {"status": "all"}).json()["count"] == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"description": "x" * 255},
        {"transaction_id": "x" * 64},
        {"transaction_id": 123},
        {"account_number": "NL" + "1" * 8},
        {"account_number": "NL" + "1" * 32},
        {"currency": "USD"},
    ],
)
def test_valid_boundaries_remain_categorised(submit, changes):
    assert submit(**changes)["status"] == "categorised"


@pytest.mark.parametrize(
    "timestamp,expected,warning",
    [
        ("2024-01-15 12:00:00", "2024-01-15T11:00:00+00:00", False),
        ("2024-07-15T12:00:00", "2024-07-15T10:00:00+00:00", False),
        ("2024-01-15T12:00:00+03:00", "2024-01-15T09:00:00+00:00", False),
        ("2024-10-27 02:30:00", "2024-10-27T00:30:00+00:00", True),
        ("2024-01-15T12:00:00.123456Z", "2024-01-15T12:00:00.123456+00:00", False),
    ],
)
def test_timestamp_interpretation_and_dst_overlap(submit, timestamp, expected, warning):
    body = submit(timestamp=timestamp)
    assert body["status"] == "categorised"
    assert datetime.fromisoformat(body["timestamp"].replace("Z", "+00:00")) == (
        datetime.fromisoformat(expected)
    )
    overlap = [issue for issue in body["issues"] if issue["code"] == "ambiguous_local_time"]
    assert bool(overlap) == warning
    if warning:
        assert_issue(body, "ambiguous_local_time", "timestamp", "warning")


def test_nonexistent_amsterdam_local_time_is_quarantined(submit):
    body = submit(timestamp="2024-03-31 02:30:00")
    assert body["status"] == "quarantined"
    assert_issue(body, "nonexistent_local_time", "timestamp")


def test_explicit_offset_in_dst_gap_is_a_valid_instant(submit):
    assert submit(timestamp="2024-03-31T02:30:00+01:00")["status"] == "categorised"
