import hashlib
import pytest

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import HttpResponse


@pytest.fixture
def client(db):
    return Client()


@pytest.fixture
def test_hash(request):
    """Generate a test hash based on the test name."""
    return hashlib.md5(request.node.name.encode()).hexdigest()


@pytest.fixture
def testuser_data(test_hash):
    """Minimal good user registration data."""
    return {
        "email": f"testuser_{test_hash}@test.com",
        "first_name": "Test first name",
        "last_name": "Test last name",
        "password": test_hash,
    }


@pytest.fixture
def create_user(db, client):
    """Create a user with given signup data."""

    def impl(signup_data):
        response: HttpResponse = client.post(
            reverse("register"),
            data=signup_data,
        )
        if response.status_code == 302:
            return response, User.objects.get(email=signup_data["email"])
        else:
            return response, None

    return impl


@pytest.fixture
def setup_testuser(create_user, testuser_data):
    """Fixture to create and login a user."""
    response, user = create_user(testuser_data)
    assert response.status_code == 302, f"Registration failed: {response}"  # Should redirect after successful registration
    assert user is not None
    return response, user
