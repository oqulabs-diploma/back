from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse


def test_registration_success(setup_testuser):
    """Test successful registration."""
    # Register user
    response, user = setup_testuser
    assert user
    assert response.url == reverse("home")
    assert User.objects.filter(email=user.email).exists()
    assert User.objects.all().count() == 1


def test_fail_user_registration_with_no_data(create_user):
    """Test registration with no one data."""
    # Make sure no users are present
    assert User.objects.all().count() == 0, "There must not be any user in the database"

    # Register user with no data
    response, user = create_user({})
    assert response.status_code == 200, f"Registration should fail with no data (here 200 is expected)"
    assert not user
    assert User.objects.all().count() == 0


def test_fail_user_registration_with_no_first_name(create_user, testuser_data):
    """Test registration with no first name."""
    # Make sure no users are present
    assert User.objects.all().count() == 0, "There must not be any user in the database"

    # Register user with no first name
    testuser_data.pop("first_name")
    response, user = create_user(testuser_data)
    assert response.status_code == 200, f"Registration should fail with no first name (here 200 is expected)"
    assert not user
    assert User.objects.all().count() == 0


def test_fail_user_registration_with_no_last_name(create_user, testuser_data):
    """Test registration with no last name."""
    # Make sure no users are present
    assert User.objects.all().count() == 0, "There must not be any user in the database"

    # Register user with no last name
    testuser_data.pop("last_name")
    response, user = create_user(testuser_data)
    assert response.status_code == 200, f"Registration should fail with no last name (here 200 is expected)"
    assert not user
    assert User.objects.all().count() == 0


def test_fail_user_registration_with_no_password(create_user, testuser_data):
    """Test registration with no password."""
    # Make sure no users are present
    assert User.objects.all().count() == 0, "There must not be any user in the database"

    # Register user with no password
    testuser_data.pop("password")
    response, user = create_user(testuser_data)
    assert response.status_code == 200, f"Registration should fail with no password (here 200 is expected)"
    assert not user
    assert User.objects.all().count() == 0


def test_fail_user_registration_with_no_email(create_user, testuser_data):
    """Test registration with no email."""
    # Make sure no users are present
    assert User.objects.all().count() == 0, "There must not be any user in the database"

    # Register user with no email
    testuser_data.pop("email")
    response, user = create_user(testuser_data)
    assert response.status_code == 200, f"Registration should fail with no email (here 200 is expected)"
    assert not user
    assert User.objects.all().count() == 0


def test_successful_no_influence_extra_fields(create_user, testuser_data):
    """Test registration with extra fields."""
    # Make sure no users are present
    assert User.objects.all().count() == 0, "There must not be any user in the database"

    # Register user with extra field
    response, user = create_user(testuser_data | {"username": "Test Username"})
    assert response.status_code == 302, f"Registration failed: {response}"
    assert User.objects.all().count() == 1
    assert User.objects.filter(email=testuser_data["email"]).exists()
    assert not hasattr(user, "extra_field")


def test_failed_registration_with_wrong_email(create_user, testuser_data):
    """Test failed registration with wrong email."""
    # Make sure no users are present
    assert User.objects.all().count() == 0, "There must not be any user in the database"

    # Register user with wrong email
    response, user = create_user(testuser_data | {"email": "wrong_email"})
    assert response.status_code == 200, f"Registration should fail with wrong email (here 200 is expected)"
    assert not user
    assert User.objects.all().count() == 0


def test_failed_registration_with_wrong_data_type(create_user, testuser_data):
    """Test failed registration with wrong data type."""
    # Make sure no users are present
    assert User.objects.all().count() == 0, "There must not be any user in the database"

    # Register user with wrong data type for email
    response, user = create_user(testuser_data | {"email": 123456})
    assert response.status_code == 200, f"Registration should fail with wrong data type (here 200 is expected)"
    assert not user
    assert User.objects.all().count() == 0

    # Register user with wrong data type for first name
    response, user = create_user(testuser_data | {"first_name": set()})
    assert response.status_code == 200, f"Registration should fail with wrong data type (here 200 is expected)"
    assert not user
    assert User.objects.all().count() == 0

    # Register user with wrong data type for first name
    response, user = create_user(testuser_data | {"last_name": list()})
    assert response.status_code == 200, f"Registration should fail with wrong data type (here 200 is expected)"
    assert not user
    assert User.objects.all().count() == 0

    # Register user with wrong data type for password
    response, user = create_user(testuser_data | {"password": dict()})
    assert response.status_code == 200, f"Registration should fail with wrong data type (here 200 is expected)"
    assert not user
    assert User.objects.all().count() == 0


def test_failed_registration_with_already_existed_user(client, testuser_data):
    """Test failed registration with existing user."""
    # Make sure no users are present
    assert User.objects.all().count() == 0, "There must not be any user in the database"

    # Register first user successfully
    response_a = client.post(
        reverse("register"),
        data=testuser_data,
    )
    assert response_a.status_code == 302, f"Registration failed: {response_a}"
    assert User.objects.all().count() == 1, "There should be only one user in the database"

    # Register second user with the same email (must fail)
    client_b: Client = Client()
    response_b = client_b.post(
        reverse("register"),
        data=testuser_data,
    )
    assert response_b.status_code == 200, "Registration should fail with existing user (here 200 is expected as a fail)"
    assert User.objects.all().count() == 1, "There should be only one user in the database"
