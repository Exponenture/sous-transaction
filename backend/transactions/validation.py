"""Parse a raw submission into typed fields plus issues. Pure: no DB, no network."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils.dateparse import parse_datetime

BLOCKING = "blocking"
WARNING = "warning"
REQUIRED = (
    "transaction_id",
    "amount",
    "timestamp",
    "description",
    "transaction_type",
    "account_number",
)
ISSUE_CODES = (
    "missing_field",
    "invalid_amount",
    "zero_amount",
    "invalid_timestamp",
    "future_timestamp",
    "nonexistent_local_time",
    "invalid_transaction_type",
    "sign_type_mismatch",
    "invalid_currency",
    "invalid_account_number",
    "invalid_description",
    "invalid_transaction_id",
    "ambiguous_local_time",
    "categorisation_fallback",
)
FUTURE_TOLERANCE = timedelta(minutes=5)
MAX_AMOUNT = Decimal(10) ** 12
CENT = Decimal("0.01")
ACCOUNT_RE = re.compile(r"[A-Z]{2}[A-Z0-9]{8,32}")
CURRENCY_RE = re.compile(r"[A-Z]{3}")


def issue(code, field, message, severity=BLOCKING):
    return {"code": code, "field": field, "severity": severity, "message": message}


def has_blocking(issues):
    return any(i["severity"] == BLOCKING for i in issues)


class Invalid(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


@dataclass
class Parsed:
    values: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)


def _blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _transaction_id(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise Invalid("invalid_transaction_id", "Must be a string or integer.")
    value = str(value).strip()
    if len(value) > 64:
        raise Invalid("invalid_transaction_id", "Must be at most 64 characters.")
    return value


def _amount(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise Invalid("invalid_amount", "Must be a number or numeric string.")
    try:
        amount = Decimal(repr(value) if isinstance(value, float) else str(value).strip())
    except InvalidOperation:
        raise Invalid("invalid_amount", "Not a decimal number.") from None
    if not amount.is_finite():
        raise Invalid("invalid_amount", "Must be finite.")
    if abs(amount) >= MAX_AMOUNT:
        raise Invalid("invalid_amount", "Must be less than 10^12 in absolute value.")
    if amount != amount.quantize(CENT):
        raise Invalid("invalid_amount", "At most 2 decimal places.")
    if amount == 0:
        raise Invalid("zero_amount", "Amount is zero.")
    return amount.quantize(CENT)


def _timestamp(value, issues):
    if not isinstance(value, str):
        raise Invalid("invalid_timestamp", "Must be an ISO 8601 string.")
    try:
        parsed = parse_datetime(value.strip())
    except ValueError:
        parsed = None
    if parsed is None:
        raise Invalid("invalid_timestamp", "Not a valid ISO 8601 datetime.")
    if parsed.tzinfo is not None:
        return parsed
    # Naive: local time in settings.TIME_ZONE (NOTES A1). Detect DST gaps and overlaps.
    tz = ZoneInfo(settings.TIME_ZONE)
    first, second = parsed.replace(tzinfo=tz, fold=0), parsed.replace(tzinfo=tz, fold=1)
    if first.utcoffset() != second.utcoffset():
        if first.astimezone(ZoneInfo("UTC")).astimezone(tz).replace(tzinfo=None) != parsed:
            raise Invalid("nonexistent_local_time", "Local time skipped by a DST change.")
        issues.append(
            issue(
                "ambiguous_local_time",
                "timestamp",
                "Local time repeats at a DST change; first occurrence assumed.",
                WARNING,
            )
        )
    return first


def _description(value):
    if not isinstance(value, str):
        raise Invalid("invalid_description", "Must be a string.")
    value = value.strip()
    if len(value) > 255:
        raise Invalid("invalid_description", "Must be at most 255 characters.")
    return value


def _transaction_type(value):
    if isinstance(value, str) and value.strip().lower() in ("debit", "credit"):
        return value.strip().lower()
    raise Invalid("invalid_transaction_type", "Must be 'debit' or 'credit'.")


def _account_number(value):
    if isinstance(value, str):
        value = re.sub(r"\s+", "", value).upper()
        if ACCOUNT_RE.fullmatch(value):
            return value
    raise Invalid("invalid_account_number", "Must be 2 letters then 8-32 letters or digits.")


def _currency(value):
    if isinstance(value, str) and CURRENCY_RE.fullmatch(value.strip().upper()):
        return value.strip().upper()
    raise Invalid("invalid_currency", "Must be a 3-letter currency code.")


def validate(payload: dict, *, now: datetime) -> Parsed:
    """Evaluate every rule; parsed fields are kept, failed ones are None."""
    result = Parsed()
    parsers = {
        "transaction_id": _transaction_id,
        "amount": _amount,
        "timestamp": lambda v: _timestamp(v, result.issues),
        "description": _description,
        "transaction_type": _transaction_type,
        "account_number": _account_number,
    }
    for name, parse in parsers.items():
        value = payload.get(name)
        result.values[name] = None
        if _blank(value):
            result.issues.append(issue("missing_field", name, f"'{name}' is required."))
            continue
        try:
            result.values[name] = parse(value)
        except Invalid as exc:
            result.issues.append(issue(exc.code, name, exc.message))

    currency = payload.get("currency")
    result.values["currency"] = "EUR"
    if not _blank(currency):
        try:
            result.values["currency"] = _currency(currency)
        except Invalid as exc:
            result.values["currency"] = None
            result.issues.append(issue(exc.code, "currency", exc.message))

    ts = result.values["timestamp"]
    if ts is not None and ts > now + FUTURE_TOLERANCE:
        result.issues.append(issue("future_timestamp", "timestamp", "Timestamp is in the future."))

    amount, kind = result.values["amount"], result.values["transaction_type"]
    if amount is not None and kind is not None and (amount > 0) != (kind == "credit"):
        result.issues.append(
            issue(
                "sign_type_mismatch",
                "amount",
                "Debits must be negative and credits positive.",
            )
        )
    return result
