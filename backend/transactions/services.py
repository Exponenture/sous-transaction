import logging

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import exceptions, status

from transactions import categorisation, validation
from transactions.models import Transaction

logger = logging.getLogger(__name__)


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
    parsed = validation.validate(payload, now=timezone.now())
    values, issues = parsed.values, parsed.issues
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
