import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.models import Account
from accounts.tests.factories import AccountFactory
from categories.models import Category
from households.models import HouseholdMembership
from households.tests.factories import HouseholdFactory, HouseholdMembershipFactory
from transactions.models import Transaction
from transactions.tests.factories import CategoryFactory, TransactionFactory
from users.tests.factories import UserFactory


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


TODAY = datetime.date.today().isoformat()


@pytest.mark.django_db
class TestTransactionCreate:
    def test_create_expense(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {
                "account": str(account.id),
                "category": str(category.id),
                "type": "expense",
                "amount": "50.00",
                "date": TODAY,
            },
        )
        assert response.status_code == 201
        transaction = Transaction.objects.get(id=response.data["id"])
        assert transaction.user_id == user.id
        assert transaction.currency == account.currency

    def test_create_income(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {
                "account": str(account.id),
                "category": str(category.id),
                "type": "income",
                "amount": "1000.00",
                "date": TODAY,
            },
        )
        assert response.status_code == 201

    def test_create_transfer(self):
        user = UserFactory()
        source = AccountFactory(user=user)
        destination = AccountFactory(user=user)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {
                "account": str(source.id),
                "to_account": str(destination.id),
                "type": "transfer",
                "amount": "200.00",
                "date": TODAY,
            },
        )
        assert response.status_code == 201
        transaction = Transaction.objects.get(id=response.data["id"])
        assert transaction.category is None

    def test_amount_must_be_positive(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {
                "account": str(account.id),
                "category": str(category.id),
                "type": "expense",
                "amount": "0.00",
                "date": TODAY,
            },
        )
        assert response.status_code == 400

    def test_expense_requires_category(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {"account": str(account.id), "type": "expense", "amount": "10.00", "date": TODAY},
        )
        assert response.status_code == 400

    def test_category_kind_must_match_transaction_type(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {
                "account": str(account.id),
                "category": str(income_category.id),
                "type": "expense",
                "amount": "10.00",
                "date": TODAY,
            },
        )
        assert response.status_code == 400

    def test_transfer_cannot_have_category(self):
        user = UserFactory()
        source = AccountFactory(user=user)
        destination = AccountFactory(user=user)
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {
                "account": str(source.id),
                "to_account": str(destination.id),
                "category": str(category.id),
                "type": "transfer",
                "amount": "10.00",
                "date": TODAY,
            },
        )
        assert response.status_code == 400

    def test_transfer_requires_different_accounts(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {
                "account": str(account.id),
                "to_account": str(account.id),
                "type": "transfer",
                "amount": "10.00",
                "date": TODAY,
            },
        )
        assert response.status_code == 400

    def test_cannot_use_another_users_account(self):
        user = UserFactory()
        other_account = AccountFactory(user=UserFactory())
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {
                "account": str(other_account.id),
                "category": str(category.id),
                "type": "expense",
                "amount": "10.00",
                "date": TODAY,
            },
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestTransactionListAndFilter:
    def test_list_only_returns_own_transactions(self):
        user = UserFactory()
        TransactionFactory.create_batch(2, user=user)
        TransactionFactory.create_batch(3, user=UserFactory())

        client = authed_client(user)
        response = client.get("/api/transactions/")
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_filter_by_type(self):
        user = UserFactory()
        TransactionFactory(user=user, type=Transaction.Type.EXPENSE)
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        TransactionFactory(user=user, type=Transaction.Type.INCOME, category=income_category)

        client = authed_client(user)
        response = client.get("/api/transactions/", {"type": "income"})
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_filter_by_date_range(self):
        user = UserFactory()
        TransactionFactory(user=user, date=datetime.date(2026, 1, 1))
        TransactionFactory(user=user, date=datetime.date(2026, 6, 1))

        client = authed_client(user)
        response = client.get(
            "/api/transactions/", {"date_from": "2026-05-01", "date_to": "2026-12-31"}
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_filter_is_shared(self):
        user = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=user, household=household, role=HouseholdMembership.Role.OWNER
        )
        TransactionFactory(user=user, household=household)
        TransactionFactory(user=user)

        client = authed_client(user)
        response = client.get("/api/transactions/", {"is_shared": "true"})
        assert response.status_code == 200
        assert response.data["count"] == 1


@pytest.mark.django_db
class TestTransactionUpdateDelete:
    def test_update_own_transaction(self):
        user = UserFactory()
        transaction = TransactionFactory(user=user, description="Old")
        client = authed_client(user)

        response = client.patch(f"/api/transactions/{transaction.id}/", {"description": "New"})
        assert response.status_code == 200
        transaction.refresh_from_db()
        assert transaction.description == "New"

    def test_delete_own_transaction(self):
        user = UserFactory()
        transaction = TransactionFactory(user=user)
        client = authed_client(user)

        response = client.delete(f"/api/transactions/{transaction.id}/")
        assert response.status_code == 204
        assert not Transaction.objects.filter(id=transaction.id).exists()

    def test_cannot_retitle_to_another_users_account(self):
        user = UserFactory()
        transaction = TransactionFactory(user=user)
        someone_elses_account = AccountFactory(user=UserFactory())
        client = authed_client(user)

        response = client.patch(
            f"/api/transactions/{transaction.id}/", {"account": str(someone_elses_account.id)}
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestTransactionCrossUserIsolation:
    def test_cannot_retrieve_another_users_personal_transaction(self):
        transaction = TransactionFactory()
        client = authed_client(UserFactory())
        response = client.get(f"/api/transactions/{transaction.id}/")
        assert response.status_code == 404

    def test_cannot_update_another_users_transaction(self):
        transaction = TransactionFactory(description="Original")
        client = authed_client(UserFactory())
        response = client.patch(
            f"/api/transactions/{transaction.id}/", {"description": "Hijacked"}
        )
        assert response.status_code == 404
        transaction.refresh_from_db()
        assert transaction.description == "Original"

    def test_unauthenticated_request_is_rejected(self):
        transaction = TransactionFactory()
        client = APIClient()
        response = client.get(f"/api/transactions/{transaction.id}/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestHouseholdSharedTransactions:
    def test_creating_shared_transaction_requires_membership(self):
        user = UserFactory()
        household = HouseholdFactory()  # user is NOT a member
        account = AccountFactory(user=user)
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {
                "account": str(account.id),
                "category": str(category.id),
                "household": str(household.id),
                "type": "expense",
                "amount": "10.00",
                "date": TODAY,
            },
        )
        assert response.status_code == 403

    def test_shared_transaction_visible_to_other_household_member(self):
        owner = UserFactory()
        other_member = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=owner, household=household, role=HouseholdMembership.Role.OWNER
        )
        HouseholdMembershipFactory(
            user=other_member, household=household, role=HouseholdMembership.Role.MEMBER
        )
        transaction = TransactionFactory(user=owner, household=household)

        client = authed_client(other_member)
        response = client.get(f"/api/transactions/{transaction.id}/")
        assert response.status_code == 200

    def test_personal_transaction_not_visible_to_household_member(self):
        owner = UserFactory()
        other_member = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=owner, household=household, role=HouseholdMembership.Role.OWNER
        )
        HouseholdMembershipFactory(
            user=other_member, household=household, role=HouseholdMembership.Role.MEMBER
        )
        transaction = TransactionFactory(user=owner, household=None)

        client = authed_client(other_member)
        response = client.get(f"/api/transactions/{transaction.id}/")
        assert response.status_code == 404

    def test_other_household_member_can_edit_shared_transaction(self):
        owner = UserFactory()
        other_member = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=owner, household=household, role=HouseholdMembership.Role.OWNER
        )
        HouseholdMembershipFactory(
            user=other_member, household=household, role=HouseholdMembership.Role.MEMBER
        )
        transaction = TransactionFactory(user=owner, household=household, description="Rent")

        client = authed_client(other_member)
        response = client.patch(
            f"/api/transactions/{transaction.id}/", {"description": "Rent (August)"}
        )
        assert response.status_code == 200
        transaction.refresh_from_db()
        assert transaction.description == "Rent (August)"


@pytest.mark.django_db
class TestAccountBalance:
    def test_balance_reflects_income_expense_and_transfers(self):
        user = UserFactory()
        checking = AccountFactory(user=user)
        savings = AccountFactory(user=user)
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        expense_category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)

        TransactionFactory(
            user=user, account=checking, category=income_category,
            type=Transaction.Type.INCOME, amount=Decimal("1000.00"),
        )
        TransactionFactory(
            user=user, account=checking, category=expense_category,
            type=Transaction.Type.EXPENSE, amount=Decimal("200.00"),
        )
        TransactionFactory(
            user=user, account=checking, to_account=savings, category=None,
            type=Transaction.Type.TRANSFER, amount=Decimal("300.00"),
        )

        checking.refresh_from_db()
        savings.refresh_from_db()
        assert checking.balance == Decimal("500.00")  # 1000 - 200 - 300
        assert savings.balance == Decimal("300.00")

    def test_account_with_no_transactions_has_zero_balance(self):
        account = AccountFactory()
        assert account.balance == Decimal("0")


@pytest.mark.django_db
class TestProtectedDeletion:
    def test_cannot_delete_account_with_transactions(self):
        user = UserFactory()
        transaction = TransactionFactory(user=user)
        client = authed_client(user)

        response = client.delete(f"/api/accounts/{transaction.account.id}/")
        assert response.status_code == 400
        assert Account.objects.filter(id=transaction.account.id).exists()

    def test_cannot_delete_category_with_transactions(self):
        user = UserFactory()
        transaction = TransactionFactory(user=user)
        client = authed_client(user)

        response = client.delete(f"/api/categories/{transaction.category.id}/")
        assert response.status_code == 400
        assert Category.objects.filter(id=transaction.category.id).exists()
