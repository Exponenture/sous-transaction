"""Small-data admin HTTP contracts from NOTES.md, especially amendment AM4."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.apps import apps
from django.contrib.messages import ERROR, get_messages
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def reviewer():
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def review_client(reviewer):
    client = Client()
    client.force_login(reviewer)
    return client


@pytest.fixture
def review_row(submit):
    body = submit(amount="12.50")  # One realistic sign mismatch, not a dataset import.
    model = apps.get_model("transactions", "Transaction")
    return model.objects.get(pk=body["id"])


def list_url():
    return reverse("admin:transactions_transaction_changelist")


def change_url(row):
    return reverse("admin:transactions_transaction_change", args=[row.pk])


def run_action(client, row, verb):
    page = client.get(list_url())
    assert page.status_code == 200
    choices = page.context["action_form"].fields["action"].choices
    actions = [value for value, label in choices if verb in str(label).lower()]
    assert len(actions) == 1, f"Expected one {verb} action, got {choices}"
    return client.post(
        list_url(),
        {
            "action": actions[0],
            "_selected_action": str(row.pk),
            "index": "0",
        },
        follow=True,
    )


@pytest.mark.parametrize("authenticated", [False, True])
def test_non_staff_cannot_access_review_queue(review_row, authenticated):
    client = Client()
    if authenticated:
        client.force_login(UserFactory(is_staff=False))
    for url in (list_url(), change_url(review_row)):
        response = client.get(url)
        assert response.status_code == 302
        assert "/admin/login/" in response.url
    review_row.refresh_from_db()
    assert review_row.status == "quarantined"


def test_staff_without_model_permission_cannot_review(review_row):
    client = Client()
    client.force_login(UserFactory(is_staff=True, is_superuser=False))
    assert client.get(list_url()).status_code == 403
    assert client.get(change_url(review_row)).status_code == 403


def test_approve_uses_corrected_fields_keeps_category_and_raw_input(
    review_client, reviewer, review_row, settings
):
    original = review_row.raw_payload.copy()
    type(review_row).objects.filter(pk=review_row.pk).update(
        amount=Decimal("-12.50"), category="Healthcare"
    )
    settings.ANTHROPIC_API_KEY = "test-key-not-a-secret"
    before = timezone.now()
    with patch("transactions.categorisation.anthropic.Anthropic") as constructor:
        response = run_action(review_client, review_row, "approve")
    assert response.status_code == 200
    constructor.assert_not_called()
    review_row.refresh_from_db()
    assert review_row.status == "categorised"
    assert review_row.category == "Healthcare"
    assert review_row.amount == Decimal("-12.50")
    assert review_row.raw_payload == original
    assert review_row.reviewed_by_id == reviewer.pk
    assert before <= review_row.reviewed_at <= timezone.now()
    assert review_row.reviewed_at.utcoffset() is not None
    assert not any(issue["severity"] == "blocking" for issue in review_row.issues)
    assert any(issue["code"] == "categorisation_fallback" for issue in review_row.issues)


def test_approve_recomputes_issues_and_displays_error_when_still_invalid(review_client, review_row):
    type(review_row).objects.filter(pk=review_row.pk).update(issues=[])
    response = run_action(review_client, review_row, "approve")
    assert response.status_code == 200
    review_row.refresh_from_db()
    assert review_row.status == "quarantined"
    assert any(issue["code"] == "sign_type_mismatch" for issue in review_row.issues)
    assert review_row.reviewed_by_id is None
    assert review_row.reviewed_at is None
    assert any(message.level == ERROR for message in get_messages(response.wsgi_request))


def test_reject_records_reviewer_and_leaves_original_data(review_client, reviewer, review_row):
    raw, issues = review_row.raw_payload.copy(), list(review_row.issues)
    before = timezone.now()
    response = run_action(review_client, review_row, "reject")
    assert response.status_code == 200
    review_row.refresh_from_db()
    assert review_row.status == "rejected"
    assert review_row.reviewed_by_id == reviewer.pk
    assert before <= review_row.reviewed_at <= timezone.now()
    assert review_row.raw_payload == raw
    assert review_row.issues == issues


@pytest.mark.parametrize("initial_status", ["categorised", "rejected"])
@pytest.mark.parametrize("verb", ["approve", "reject"])
def test_actions_do_not_change_rows_outside_quarantine(
    review_client, review_row, initial_status, verb
):
    type(review_row).objects.filter(pk=review_row.pk).update(
        amount=Decimal("-12.50"), status=initial_status
    )
    run_action(review_client, review_row, verb)
    review_row.refresh_from_db()
    assert review_row.status == initial_status
    assert review_row.reviewed_by_id is None
    assert review_row.reviewed_at is None


def test_raw_payload_is_read_only_in_review_form(review_client, review_row):
    response = review_client.get(change_url(review_row))
    assert response.status_code == 200
    form = response.context["adminform"]
    assert "raw_payload" in form.readonly_fields
    assert "raw_payload" not in form.form.fields


def test_queue_filters_by_status_and_issue_code(review_client, review_row, submit):
    clean = submit(transaction_id="admin-clean")
    response = review_client.get(list_url(), {"status__exact": "quarantined"})
    assert response.status_code == 200
    assert [str(row.pk) for row in response.context["cl"].result_list] == [str(review_row.pk)]
    specs = response.context["cl"].filter_specs
    issue_filters = [spec for spec in specs if "issue" in str(spec.title).lower()]
    assert len(issue_filters) == 1
    parameters = issue_filters[0].expected_parameters()
    assert len(parameters) == 1
    response = review_client.get(list_url(), {parameters[0]: "sign_type_mismatch"})
    assert response.status_code == 200
    ids = [str(row.pk) for row in response.context["cl"].result_list]
    assert ids == [str(review_row.pk)]
    assert clean["id"] not in ids


def test_rejected_row_is_retrievable_and_replay_preserves_review_status(
    review_client, review_row, auth_client
):
    run_action(review_client, review_row, "reject")
    url = "/api/transactions/"
    detail = auth_client.get(f"{url}{review_row.pk}/")
    assert detail.status_code == 200
    assert detail.json()["status"] == "rejected"
    listing = auth_client.get(url, {"status": "rejected"})
    assert [row["id"] for row in listing.json()["results"]] == [str(review_row.pk)]
    assert auth_client.get(url).json()["count"] == 0
    replay = auth_client.post(url, review_row.raw_payload, format="json")
    assert replay.status_code == 200
    assert replay.json()["status"] == "rejected"
