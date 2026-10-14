import pytest


@pytest.fixture(autouse=True)
def isolated_transaction_environment(settings, monkeypatch):
    """No live AI credentials or shared throttle state."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    settings.ANTHROPIC_API_KEY = ""
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_CLASSES": [],
    }


@pytest.fixture
def transaction_payload():
    return {
        "transaction_id": "bank-001",
        "amount": "-12.50",
        "timestamp": "2024-01-15T12:00:00+01:00",
        "description": "Unrecognised merchant zxqv",
        "transaction_type": "debit",
        "account_number": "NL91ABNA0417164300",
    }


@pytest.fixture
def submit(auth_client, transaction_payload):
    def create(**changes):
        response = auth_client.post(
            "/api/transactions/", {**transaction_payload, **changes}, format="json"
        )
        assert response.status_code == 201, response.content
        return response.json()

    return create
