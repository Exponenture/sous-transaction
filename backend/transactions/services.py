import logging
from datetime import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import exceptions, status

from transactions import categorisation, validation
from transactions.models import Transaction

logger = logging.getLogger(__name__)


REVIEWED_FIELDS = (
    "transaction_id",
    "amount",
    "currency",
    "timestamp",
    "description",
    "transaction_type",
    "account_number",
)


class TransactionConflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"
    default_detail = "transaction_id already used with a different payload."


def same_json(a, b) -> bool:
    """JSON equality per NOTES AM3: numbers by value, but never str == number or bool == int."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_json(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(map(same_json, a, b))
    return type(a) is type(b) and a == b


def _replay(existing: Transaction, payload: dict) -> tuple[Transaction, bool]:
    if not same_json(existing.raw_payload, payload):
        raise TransactionConflict()
    return existing, False


def submit_transaction(*, owner, payload: dict) -> tuple[Transaction, bool]:
    """Store a submission (clean or quarantined). Returns (row, created); replays aren't created."""
    payload, issues = validation.sanitise(payload)
    parsed = validation.validate(payload, now=timezone.now())
    values, issues = parsed.values, issues + parsed.issues
    key = values["transaction_id"]
    if key is not None:
        existing = Transaction.objects.filter(owner=owner, transaction_id=key).first()
        if existing:
            return _replay(existing, payload)

    result = categorisation.categorise(
        description=values["description"],
        amount=values["amount"],
        transaction_type=values["transaction_type"],
    )
    if result.fell_back:
        issues.append(
            validation.issue(
                "categorisation_fallback",
                None,
                "AI categorisation unavailable; keyword rules used.",
                validation.WARNING,
            )
        )
    blocking = validation.has_blocking(issues)
    try:
        with transaction.atomic():
            row = Transaction.objects.create(
                owner=owner,
                **values,
                category=result.category,
                categorisation_source=result.source,
                status=Transaction.Status.QUARANTINED
                if blocking
                else Transaction.Status.CATEGORISED,
                issues=issues,
                raw_payload=payload,
            )
    except IntegrityError:
        if key is None:
            raise
        # Lost a race with an identical-key submission: treat as a replay of the winner.
        return _replay(Transaction.objects.get(owner=owner, transaction_id=key), payload)

    logger.info(
        "transaction_stored id=%s status=%s issues=%s",
        row.pk,
        row.status,
        ",".join(i["code"] for i in issues) or "-",
    )
    return row, True


def _as_json(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _revalidate(row: Transaction) -> list:
    """Blocking issues recomputed from the stored (reviewer-edited) fields; warnings kept (AM4)."""
    payload = {name: _as_json(getattr(row, name)) for name in REVIEWED_FIELDS}
    issues = [
        i
        for i in validation.validate(payload, now=timezone.now()).issues
        if i["severity"] == validation.BLOCKING
    ]
    for name in ("currency", "category"):
        if getattr(row, name) is None:
            issues.append(validation.issue("missing_field", name, f"'{name}' is required."))
    return issues + [i for i in row.issues if i["severity"] == validation.WARNING]


def approve_transaction(*, pk, reviewer) -> tuple[Transaction, bool]:
    """Quarantined rows only. Returns (row, approved); never calls the LLM."""
    with transaction.atomic():
        row = Transaction.objects.select_for_update().get(pk=pk)
        if row.status != Transaction.Status.QUARANTINED:
            return row, False
        row.issues = _revalidate(row)
        if validation.has_blocking(row.issues):
            row.save(update_fields=["issues", "updated_at"])
            return row, False
        row.status = Transaction.Status.CATEGORISED
        row.reviewed_by, row.reviewed_at = reviewer, timezone.now()
        row.save(update_fields=["issues", "status", "reviewed_by", "reviewed_at", "updated_at"])
    logger.info("transaction_approved id=%s", row.pk)
    return row, True


def reject_transaction(*, pk, reviewer) -> tuple[Transaction, bool]:
    """Quarantined rows only. Returns (row, rejected)."""
    with transaction.atomic():
        row = Transaction.objects.select_for_update().get(pk=pk)
        if row.status != Transaction.Status.QUARANTINED:
            return row, False
        row.status = Transaction.Status.REJECTED
        row.reviewed_by, row.reviewed_at = reviewer, timezone.now()
        row.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
    logger.info("transaction_rejected id=%s", row.pk)
    return row, True
