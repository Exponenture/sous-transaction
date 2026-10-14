import pytest
from rest_framework.test import APIClient

from core.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client):
    api_client.force_authenticate(UserFactory())
    return api_client
