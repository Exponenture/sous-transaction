"""PostgreSQL invariants named in NOTES.md, independent of service implementation."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.apps import apps
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError
from rest_framework.test import APIClient

from core.tests.factories import UserFactory

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


@pytest.fixture
def stored_transaction(submit):
    body = submit()
    models = [model for model in apps.get_models() if model.__name__ == "Transaction"]
    assert len(models) == 1, "The spec requires one Transaction model"
    return models[0].objects.get(pk=body["id"])


@pytest.mark.parametrize("category", CATEGORIES)
def test_every_predefined_category_is_supported_by_database_and_filter(
    stored_transaction, auth_client, category
):
    model = type(stored_transaction)
    model.objects.filter(pk=stored_transaction.pk).update(category=category)
    response = auth_client.get(URL, {"category": category})
    assert response.status_code == 200, response.content
    assert [row["category"] for row in response.json()["results"]] == [category]


@pytest.mark.parametrize(
    "field,value",
    [
        ("category", "Invalid"),
        ("transaction_type", "transfer"),
        ("status", "unknown"),
        ("amount", None),
        ("timestamp", None),
        ("description", None),
        ("transaction_type", None),
        ("account_number", None),
        ("category", None),
    ],
)
def test_database_rejects_invalid_categorised_rows(stored_transaction, field, value):
    model = type(stored_transaction)
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.filter(pk=stored_transaction.pk).update(**{field: value})
    stored_transaction.refresh_from_db()
    assert stored_transaction.status == "categorised"
    assert stored_transaction.category == "Miscellaneous"


def test_database_rejects_duplicate_owner_and_client_key(stored_transaction, submit):
    second = submit(transaction_id="second")
    model = type(stored_transaction)
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.filter(pk=second["id"]).update(
            transaction_id=stored_transaction.transaction_id
        )
    assert model.objects.count() == 2


def test_owner_cannot_be_deleted_while_transactions_exist(stored_transaction):
    with pytest.raises(ProtectedError):
        stored_transaction.owner.delete()


@pytest.mark.django_db(transaction=True)
def test_simultaneous_identical_submissions_create_one_row(transaction_payload):
    user = UserFactory()
    barrier = Barrier(2)

    def post():
        close_old_connections()
        try:
            client = APIClient()
            client.force_authenticate(user)
            barrier.wait(timeout=10)
            response = client.post(URL, transaction_payload, format="json")
            return response.status_code, response.content
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(post) for _ in range(2)]
        responses = [future.result(timeout=20) for future in futures]
    assert sorted(status for status, _ in responses) == [200, 201], responses
    client = APIClient()
    client.force_authenticate(user)
    response = client.get(URL, {"status": "all"})
    assert response.status_code == 200
    assert response.json()["count"] == 1
