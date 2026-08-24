import pytest
from rest_framework.test import APIClient

from users.models import User
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestRegister:
    def test_register_creates_user_and_returns_access_token(self):
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            {
                "email": "new.user@example.com",
                "password": "S0me-Strong-Pass!",
                "first_name": "New",
                "last_name": "User",
            },
        )

        assert response.status_code == 201
        assert "access" in response.data
        assert response.data["user"]["email"] == "new.user@example.com"
        # Refresh token must never appear in the JSON body.
        assert "refresh" not in response.data
        assert User.objects.filter(email="new.user@example.com").exists()

    def test_register_sets_httponly_refresh_cookie(self):
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            {"email": "cookie.user@example.com", "password": "S0me-Strong-Pass!"},
        )

        cookie = response.cookies.get("refresh_token")
        assert cookie is not None
        assert cookie["httponly"] is True
        assert cookie["samesite"] == "Lax"

    def test_register_rejects_duplicate_email(self):
        UserFactory(email="dupe@example.com")
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            {"email": "dupe@example.com", "password": "S0me-Strong-Pass!"},
        )
        assert response.status_code == 400

    def test_register_enforces_password_validation(self):
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            {"email": "weakpass@example.com", "password": "12345678"},
        )
        assert response.status_code == 400
        assert "password" in response.data


@pytest.mark.django_db
class TestLogin:
    def test_login_with_correct_credentials_succeeds(self):
        UserFactory(email="loginuser@example.com", password="CorrectPass1!")
        client = APIClient()
        response = client.post(
            "/api/auth/login/",
            {"email": "loginuser@example.com", "password": "CorrectPass1!"},
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert response.cookies.get("refresh_token") is not None

    def test_login_with_wrong_password_is_rejected(self):
        UserFactory(email="loginuser2@example.com", password="CorrectPass1!")
        client = APIClient()
        response = client.post(
            "/api/auth/login/",
            {"email": "loginuser2@example.com", "password": "WrongPassword!"},
        )
        assert response.status_code == 401

    def test_login_with_nonexistent_email_gives_same_generic_error(self):
        """
        The error for 'wrong password' and 'no such user' must be
        indistinguishable — otherwise the endpoint becomes a way to
        enumerate registered emails.
        """
        client = APIClient()
        real_user_response = client.post(
            "/api/auth/login/",
            {"email": "ghost@example.com", "password": "whatever123"},
        )
        assert real_user_response.status_code == 401
        assert str(real_user_response.data["detail"]) == "Invalid email or password."

    def test_login_rejects_inactive_user(self):
        UserFactory(email="inactive@example.com", password="CorrectPass1!", is_active=False)
        client = APIClient()
        response = client.post(
            "/api/auth/login/",
            {"email": "inactive@example.com", "password": "CorrectPass1!"},
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestRefresh:
    def test_refresh_without_cookie_is_rejected(self):
        client = APIClient()
        response = client.post("/api/auth/refresh/")
        assert response.status_code == 401

    def test_refresh_with_valid_cookie_returns_new_access_token(self):
        UserFactory(email="refreshme@example.com", password="CorrectPass1!")
        client = APIClient()
        login_response = client.post(
            "/api/auth/login/",
            {"email": "refreshme@example.com", "password": "CorrectPass1!"},
        )
        client.cookies["refresh_token"] = login_response.cookies["refresh_token"].value

        refresh_response = client.post("/api/auth/refresh/")
        assert refresh_response.status_code == 200
        assert "access" in refresh_response.data
        assert refresh_response.data["access"] != login_response.data["access"]

    def test_refresh_rotates_cookie_and_blacklists_old_token(self):
        UserFactory(email="rotateme@example.com", password="CorrectPass1!")
        client = APIClient()
        login_response = client.post(
            "/api/auth/login/",
            {"email": "rotateme@example.com", "password": "CorrectPass1!"},
        )
        old_refresh_value = login_response.cookies["refresh_token"].value
        client.cookies["refresh_token"] = old_refresh_value

        first_refresh = client.post("/api/auth/refresh/")
        assert first_refresh.status_code == 200
        new_refresh_value = first_refresh.cookies["refresh_token"].value
        assert new_refresh_value != old_refresh_value

        # Re-using the now-rotated-out refresh token must fail.
        client.cookies["refresh_token"] = old_refresh_value
        reuse_attempt = client.post("/api/auth/refresh/")
        assert reuse_attempt.status_code == 401


@pytest.mark.django_db
class TestLogout:
    def test_logout_blacklists_refresh_token_and_clears_cookie(self):
        UserFactory(email="logoutme@example.com", password="CorrectPass1!")
        client = APIClient()
        login_response = client.post(
            "/api/auth/login/",
            {"email": "logoutme@example.com", "password": "CorrectPass1!"},
        )
        access = login_response.data["access"]
        refresh_cookie_value = login_response.cookies["refresh_token"].value
        client.cookies["refresh_token"] = refresh_cookie_value

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout_response = client.post("/api/auth/logout/")
        assert logout_response.status_code == 204

        # The blacklisted refresh token can no longer mint a new access token.
        client.cookies["refresh_token"] = refresh_cookie_value
        refresh_attempt = client.post("/api/auth/refresh/")
        assert refresh_attempt.status_code == 401

    def test_logout_requires_authentication(self):
        client = APIClient()
        response = client.post("/api/auth/logout/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestMeEndpointIsolation:
    """
    The one class of bug that's non-negotiable in a finance app: a user
    must never be able to see another user's data, even by ID guessing.
    /me/ has no ID in the URL at all specifically to make that class of
    bug structurally impossible for this endpoint — every future
    resource endpoint (transactions, budgets...) must inherit the same
    'filtered by request.user' pattern from a shared base view.
    """

    def test_me_returns_only_the_authenticated_users_own_data(self):
        user_a = UserFactory(email="alice@example.com", password="AlicePass1!")
        UserFactory(email="bob@example.com", password="BobPass1!")

        client = APIClient()
        login_response = client.post(
            "/api/auth/login/",
            {"email": "alice@example.com", "password": "AlicePass1!"},
        )
        access = login_response.data["access"]

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me_response = client.get("/api/auth/me/")

        assert me_response.status_code == 200
        assert me_response.data["email"] == "alice@example.com"
        assert me_response.data["id"] == str(user_a.id)

    def test_me_requires_authentication(self):
        client = APIClient()
        response = client.get("/api/auth/me/")
        assert response.status_code == 401

    def test_expired_or_garbage_access_token_is_rejected(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        response = client.get("/api/auth/me/")
        assert response.status_code == 401
