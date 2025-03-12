from django.contrib.auth.models import User
from django.urls import reverse


def test_login_success(client, setup_testuser, testuser_data):
    """Test successful registration."""
    # Register user
    response, user = setup_testuser
    assert user
    assert response.url == reverse("home")
    assert User.objects.filter(email=user.email).exists()
    assert User.objects.all().count() == 1

    # Logout user
    response = client.get(reverse("logout"))
    assert response.url == reverse("login")

    # Login user
    response = client.post(
        reverse("login"),
        data={
            "email": testuser_data["email"],
            "password": testuser_data["password"],
        },
    )
    assert response.url == reverse("home")
    # Make sure that the user is authenticated
    assert response.wsgi_request.user.is_authenticated


def test_failed_login_with_wrong_email(client, setup_testuser, testuser_data):
    """Test login with wrong email."""
    # Register user
    response, user = setup_testuser
    assert user
    assert response.url == reverse("home")
    assert User.objects.filter(email=user.email).exists()
    assert User.objects.all().count() == 1

    # Logout user
    response = client.get(reverse("logout"))
    assert response.url == reverse("login")

    # Login user with wrong email
    response = client.post(
        reverse("login"),
        data={
            "email": "wrong_email",
            "password": testuser_data["password"],
        },
    )
    assert response.status_code == 200, "Login should fail with wrong email (here 200 is expected)"
    # Make sure that the user is not authenticated
    assert not response.wsgi_request.user.is_authenticated


def test_failed_login_with_wrong_password(client, setup_testuser, testuser_data):
    """Test login with wrong email."""
    # Register user
    response, user = setup_testuser
    assert user
    assert response.url == reverse("home")
    assert User.objects.filter(email=user.email).exists()
    assert User.objects.all().count() == 1

    # Logout user
    response = client.get(reverse("logout"))
    assert response.url == reverse("login")

    # Login user with wrong email
    response = client.post(
        reverse("login"),
        data={
            "email": testuser_data["email"],
            "password": "wrong_password",
        },
    )
    assert response.status_code == 200, "Login should fail with wrong email (here 200 is expected)"
    # Make sure that the user is not authenticated
    assert not response.wsgi_request.user.is_authenticated


def test_failed_login_with_no_data(client):
    """Test login with no data."""

    response = client.post(reverse("login"), data={})
    assert response.status_code == 200, "Login should fail with no data (here 200 is expected)"
    # Make sure that the user is not authenticated
    assert not response.wsgi_request.user.is_authenticated


def test_failed_login_with_non_existed_user(client, setup_testuser):
    """Test login with non-existed user."""
    # Register user
    response, user = setup_testuser
    assert user
    assert response.url == reverse("home")
    assert User.objects.filter(email=user.email).exists()
    assert User.objects.all().count() == 1

    # Logout user
    response = client.get(reverse("logout"))
    assert response.url == reverse("login")

    # Login user with non-existed user
    response = client.post(
        reverse("login"),
        data={
            "email": "non_existed_user",
            "password": "non_existed_password",
        },
    )
    assert response.status_code == 200, "Login should fail with non-existed user (here 200 is expected)"
    # Make sure that the user is not authenticated
    assert not response.wsgi_request.user.is_authenticated


def test_redirected_user_after_registration(client, setup_testuser):
    """Test redirection after login."""
    # Register user
    response, user = setup_testuser
    assert user
    assert response.status_code == 302, "Registration should redirect to home page"
    assert response.url == reverse("home")
    assert User.objects.filter(email=user.email).exists()
    assert User.objects.all().count() == 1

    # Login user
    response = client.post(reverse("login"))
    assert response.status_code == 302, "Login should redirect to home page"
    # Make sure that the user is authenticated
    assert response.wsgi_request.user.is_authenticated

    # Register user again
    response, user = setup_testuser
    assert response.status_code == 302, "Registration should redirect to home page"
    assert response.url == reverse("home")
    assert User.objects.all().count() == 1


def test_redirected_to_login_as_non_authenticated(client):
    """Test redirection to login page as non-authenticated user."""
    response = client.get(reverse("logout"))
    assert response.url == reverse("login")
    # Make sure that the user is not authenticated
    assert not response.wsgi_request.user.is_authenticated
