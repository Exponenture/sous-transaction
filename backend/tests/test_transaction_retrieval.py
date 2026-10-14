"""Ownership, replay and list contracts, exercised entirely through HTTP."""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from core.tests.factories import UserFactory

pytestmark = pytest.mark.django_db
URL = "/api/transactions/"


def test_identical_replay_returns_original_body_without_duplicate(auth_client, transaction_payload):
    first = auth_client.post(URL, transaction_payload, format="json")
    assert first.status_code == 201, first.content
    replay = auth_client.post(URL, transaction_payload, format="json")
    assert replay.status_code == 200, replay.content
    assert replay.json() == first.json()
    assert auth_client.get(URL, {"status": "all"}).json()["count"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": "-99.00"},
        {"description": "Changed description"},
        {"unknown_key": "changed"},
    ],
)
def test_changed_payload_conflicts_without_overwriting_original(
    auth_client, transaction_payload, changes
):
    first = auth_client.post(URL, transaction_payload, format="json")
    assert first.status_code == 201, first.content
    conflict = auth_client.post(URL, {**transaction_payload, **changes}, format="json")
    assert conflict.status_code == 409, conflict.content
    assert conflict.json()["error"]["code"] == "conflict"
    listing = auth_client.get(URL, {"status": "all"}).json()
    assert listing["count"] == 1
    detail = auth_client.get(f"{URL}{first.json()['id']}/").json()
    assert detail["raw_payload"] == transaction_payload


def test_quarantined_transaction_replays_too(auth_client, transaction_payload):
    payload = {**transaction_payload, "amount": "NaN"}
    first = auth_client.post(URL, payload, format="json")
    assert first.status_code == 201, first.content
    assert first.json()["status"] == "quarantined"
    replay = auth_client.post(URL, payload, format="json")
    assert replay.status_code == 200, replay.content
    assert replay.json() == first.json()


@pytest.mark.parametrize("key", [None, "", "x" * 65, []])
def test_invalid_key_has_no_replay_protection(auth_client, transaction_payload, key):
    payload = {**transaction_payload, "transaction_id": key}
    responses = [auth_client.post(URL, payload, format="json") for _ in range(2)]
    assert [response.status_code for response in responses] == [201, 201]
    assert all(response.json()["status"] == "quarantined" for response in responses)
    assert responses[0].json()["id"] != responses[1].json()["id"]
    assert auth_client.get(URL, {"status": "all"}).json()["count"] == 2


def test_missing_key_has_no_replay_protection(auth_client, transaction_payload):
    payload = {key: value for key, value in transaction_payload.items() if key != "transaction_id"}
    first = auth_client.post(URL, payload, format="json")
    second = auth_client.post(URL, payload, format="json")
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_two_owners_can_use_the_same_key_without_seeing_each_others_rows(
    auth_client, transaction_payload
):
    first = auth_client.post(URL, transaction_payload, format="json")
    assert first.status_code == 201, first.content
    other = APIClient()
    other.force_authenticate(UserFactory())
    second = other.post(URL, transaction_payload, format="json")
    assert second.status_code == 201, second.content
    assert first.json()["id"] != second.json()["id"]
    for client, own, foreign in [(auth_client, first, second), (other, second, first)]:
        listing = client.get(URL, {"status": "all"}).json()
        assert listing["count"] == 1
        assert [row["id"] for row in listing["results"]] == [own.json()["id"]]
        response = client.get(f"{URL}{foreign.json()['id']}/")
        assert response.status_code == 404
        assert "error" in response.json()


def test_server_owned_fields_cannot_be_overridden(submit, auth_client):
    other_user = UserFactory()
    forged_id = str(uuid4())
    body = submit(
        owner=other_user.pk,
        id=forged_id,
        status="rejected",
        category="Housing",
        categorisation_source="llm",
        issues=[],
    )
    assert body["id"] != forged_id
    assert body["status"] == "categorised"
    assert body["category"] == "Miscellaneous"
    assert body["categorisation_source"] == "rules"
    assert auth_client.get(f"{URL}{body['id']}/").status_code == 200
    other = APIClient()
    other.force_authenticate(other_user)
    assert other.get(f"{URL}{body['id']}/").status_code == 404


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", URL),
        ("get", URL),
        ("get", f"{URL}{uuid4()}/"),
    ],
)
@pytest.mark.parametrize("invalid_token", [False, True])
def test_every_endpoint_requires_authentication(api_client, method, path, invalid_token):
    if invalid_token:
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
    response = getattr(api_client, method)(path)
    assert response.status_code == 401, response.content
    assert set(response.json()["error"]) == {"code", "message", "details"}


@pytest.mark.parametrize("identifier", [str(uuid4()), "not-a-uuid", "123"])
def test_unknown_or_malformed_id_returns_enveloped_404(auth_client, identifier):
    response = auth_client.get(f"{URL}{identifier}/")
    assert response.status_code == 404
    assert set(response.json()["error"]) == {"code", "message", "details"}


def test_empty_list_has_pagination_contract(auth_client):
    response = auth_client.get(URL)
    assert response.status_code == 200, response.content
    assert response.json() == {"count": 0, "next": None, "previous": None, "results": []}


def test_default_list_hides_quarantine_but_filters_and_detail_expose_it(submit, auth_client):
    clean = submit()
    dirty = submit(transaction_id="dirty", amount="NaN")
    for params, ids in [
        ({}, [clean["id"]]),
        ({"status": "categorised"}, [clean["id"]]),
        ({"status": "quarantined"}, [dirty["id"]]),
        ({"status": "rejected"}, []),
        ({"status": "all"}, [clean["id"], dirty["id"]]),
    ]:
        response = auth_client.get(URL, params)
        assert response.status_code == 200, response.content
        data = response.json()
        assert data["count"] == len(ids)
        assert {row["id"] for row in data["results"]} == set(ids)
        assert all("raw_payload" not in row for row in data["results"])
    assert auth_client.get(f"{URL}{dirty['id']}/").json()["status"] == "quarantined"


@pytest.mark.parametrize("params", [{"status": "invalid"}, {"category": "Invalid"}])
def test_invalid_filters_return_validation_error(auth_client, params):
    response = auth_client.get(URL, params)
    assert response.status_code == 400, response.content
    assert response.json()["error"]["code"] == "validation_error"


def test_category_filter_selects_matching_rows(submit, auth_client):
    body = submit()
    response = auth_client.get(URL, {"category": "Miscellaneous"})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [body["id"]]
    assert auth_client.get(URL, {"category": "Housing"}).json()["count"] == 0


def test_list_orders_timestamps_descending_with_nulls_last(submit, auth_client):
    older = submit(transaction_id="old", timestamp="2024-01-01T00:00:00Z")
    null = submit(transaction_id="null", timestamp="bad")
    newer = submit(transaction_id="new", timestamp="2024-02-01T00:00:00Z")
    rows = auth_client.get(URL, {"status": "all"}).json()["results"]
    assert [row["id"] for row in rows] == [newer["id"], older["id"], null["id"]]


def test_pagination_returns_twenty_rows_without_loss_or_duplicates(submit, auth_client):
    rows = [
        submit(transaction_id=f"page-{index}", timestamp=f"2024-01-{index + 1:02d}T12:00:00Z")
        for index in range(21)
    ]
    first = auth_client.get(URL)
    assert first.status_code == 200
    first = first.json()
    assert first["count"] == 21
    assert len(first["results"]) == 20
    assert first["next"] is not None
    assert first["previous"] is None
    second = auth_client.get(first["next"])
    assert second.status_code == 200
    second = second.json()
    assert len(second["results"]) == 1
    assert second["next"] is None
    assert second["previous"] is not None
    ids = [row["id"] for row in first["results"] + second["results"]]
    assert len(set(ids)) == 21
    assert set(ids) == {row["id"] for row in rows}


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_api_does_not_allow_editing_or_deleting(submit, auth_client, method):
    row = submit()
    response = getattr(auth_client, method)(f"{URL}{row['id']}/", {}, format="json")
    assert response.status_code == 405, response.content
    assert auth_client.get(f"{URL}{row['id']}/").json()["amount"] == "-12.50"
