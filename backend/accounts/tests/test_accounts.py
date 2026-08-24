import pytest
from rest_framework.test import APIClient

from accounts.models import Account
from accounts.tests.factories import AccountFactory
from users.tests.factories import UserFactory


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestAccountCRUD:
    def test_create_account(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.post(
            "/api/accounts/",
            {"name": "BDO Checking", "account_type": "bank", "currency": "PHP"},
        )
        assert response.status_code == 201
        assert response.data["name"] == "BDO Checking"
        account = Account.objects.get(id=response.data["id"])
        # user must be set server-side from the authenticated request,
        # never trusted from the payload.
        assert account.user_id == user.id

    def test_create_account_ignores_client_supplied_user(self):
        user = UserFactory()
        other = UserFactory()
        client = authed_client(user)
        response = client.post(
            "/api/accounts/",
            {"name": "Sneaky", "account_type": "cash", "user": str(other.id)},
        )
        assert response.status_code == 201
        account = Account.objects.get(id=response.data["id"])
        assert account.user_id == user.id  # not other.id

    def test_duplicate_account_name_for_same_user_is_rejected(self):
        user = UserFactory()
        AccountFactory(user=user, name="Cash")
        client = authed_client(user)
        response = client.post("/api/accounts/", {"name": "Cash", "account_type": "cash"})
        assert response.status_code == 400

    def test_same_account_name_allowed_across_different_users(self):
        AccountFactory(user=UserFactory(), name="Cash")
        user_b = UserFactory()
        client = authed_client(user_b)
        response = client.post("/api/accounts/", {"name": "Cash", "account_type": "cash"})
        assert response.status_code == 201

    def test_list_only_returns_own_accounts(self):
        user = UserFactory()
        AccountFactory.create_batch(3, user=user)
        AccountFactory.create_batch(2, user=UserFactory())

        client = authed_client(user)
        response = client.get("/api/accounts/")
        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_update_own_account(self):
        user = UserFactory()
        account = AccountFactory(user=user, name="Old Name")
        client = authed_client(user)
        response = client.patch(f"/api/accounts/{account.id}/", {"name": "New Name"})
        assert response.status_code == 200
        account.refresh_from_db()
        assert account.name == "New Name"

    def test_delete_own_account(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)
        response = client.delete(f"/api/accounts/{account.id}/")
        assert response.status_code == 204
        assert not Account.objects.filter(id=account.id).exists()


@pytest.mark.django_db
class TestAccountCrossUserIsolation:
    """
    The test I owed from step 1: now that a resource has an ID in the
    URL, prove a user can't reach another user's record by guessing or
    reusing that ID — for read, write, AND delete. A 404, not a 403,
    is the correct response: the endpoint shouldn't even confirm the
    record exists.
    """

    def test_cannot_retrieve_another_users_account(self):
        owner = UserFactory()
        attacker = UserFactory()
        account = AccountFactory(user=owner)

        client = authed_client(attacker)
        response = client.get(f"/api/accounts/{account.id}/")
        assert response.status_code == 404

    def test_cannot_update_another_users_account(self):
        owner = UserFactory()
        attacker = UserFactory()
        account = AccountFactory(user=owner, name="Original")

        client = authed_client(attacker)
        response = client.patch(f"/api/accounts/{account.id}/", {"name": "Hijacked"})
        assert response.status_code == 404
        account.refresh_from_db()
        assert account.name == "Original"

    def test_cannot_delete_another_users_account(self):
        owner = UserFactory()
        attacker = UserFactory()
        account = AccountFactory(user=owner)

        client = authed_client(attacker)
        response = client.delete(f"/api/accounts/{account.id}/")
        assert response.status_code == 404
        assert Account.objects.filter(id=account.id).exists()

    def test_unauthenticated_request_is_rejected(self):
        account = AccountFactory()
        client = APIClient()
        response = client.get(f"/api/accounts/{account.id}/")
        assert response.status_code == 401
