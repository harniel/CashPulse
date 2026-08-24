import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import AccountFactory
from categories.models import Category
from common.dates import add_months
from households.models import HouseholdMembership
from households.tests.factories import HouseholdFactory, HouseholdMembershipFactory
from recurring_transactions.models import GeneratedOccurrence
from recurring_transactions.tests.factories import RecurringTransactionFactory
from transactions.models import Transaction
from transactions.tests.factories import CategoryFactory, TransactionFactory
from users.tests.factories import UserFactory

TODAY = datetime.date.today()
THIS_MONTH = TODAY.replace(day=1)


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def mark_as_recurring_generated(transaction, recurring):
    GeneratedOccurrence.objects.create(recurring=recurring, due_date=transaction.date, transaction=transaction)


@pytest.mark.django_db
class TestInsufficientData:
    def test_no_history_at_all(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.get("/api/forecast/")
        assert response.status_code == 200
        assert response.data["insufficient_data"] is True

    def test_only_one_months_history(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.INCOME,
            amount=Decimal("1000.00"), date=THIS_MONTH,
        )
        client = authed_client(user)
        response = client.get("/api/forecast/")
        assert response.data["insufficient_data"] is True

    def test_two_months_history_is_enough(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.INCOME,
            amount=Decimal("1000.00"), date=THIS_MONTH,
        )
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.INCOME,
            amount=Decimal("1000.00"), date=add_months(THIS_MONTH, -1),
        )
        client = authed_client(user)
        response = client.get("/api/forecast/")
        assert response.data["insufficient_data"] is False


@pytest.mark.django_db
class TestTrailingAverage:
    def test_average_income_and_expense_over_trailing_window(self):
        user = UserFactory()
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        expense_category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)

        for i in range(3):
            month = add_months(THIS_MONTH, -i)
            TransactionFactory(
                user=user, category=income_category, type=Transaction.Type.INCOME,
                amount=Decimal("3000.00"), date=month,
            )
            TransactionFactory(
                user=user, category=expense_category, type=Transaction.Type.EXPENSE,
                amount=Decimal("1000.00"), date=month,
            )

        client = authed_client(user)
        response = client.get("/api/forecast/", {"trailing_months": 3})
        assert response.status_code == 200
        assert Decimal(response.data["avg_monthly_income"]) == Decimal("3000.00")
        assert Decimal(response.data["avg_monthly_expenses"]) == Decimal("1000.00")
        assert Decimal(response.data["avg_monthly_savings"]) == Decimal("2000.00")

    def test_transfers_are_excluded_from_the_average(self):
        user = UserFactory()
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        TransactionFactory(
            user=user, category=income_category, type=Transaction.Type.INCOME,
            amount=Decimal("1000.00"), date=THIS_MONTH,
        )
        TransactionFactory(
            user=user, category=income_category, type=Transaction.Type.INCOME,
            amount=Decimal("1000.00"), date=add_months(THIS_MONTH, -1),
        )
        TransactionFactory(
            user=user, account=AccountFactory(user=user), type=Transaction.Type.TRANSFER, category=None,
            to_account=AccountFactory(user=user), amount=Decimal("50000.00"), date=THIS_MONTH,
        )

        client = authed_client(user)
        response = client.get("/api/forecast/", {"trailing_months": 2})
        assert Decimal(response.data["avg_monthly_income"]) == Decimal("1000.00")

    def test_recurring_attributable_transactions_are_excluded_from_the_average(self):
        user = UserFactory()
        expense_category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        recurring = RecurringTransactionFactory(
            user=user, category=expense_category, amount=Decimal("500.00")
        )
        # Two months of "manual" expenses feeding the average...
        TransactionFactory(
            user=user, category=expense_category, type=Transaction.Type.EXPENSE,
            amount=Decimal("200.00"), date=THIS_MONTH,
        )
        TransactionFactory(
            user=user, category=expense_category, type=Transaction.Type.EXPENSE,
            amount=Decimal("200.00"), date=add_months(THIS_MONTH, -1),
        )
        # ...plus a recurring-generated one that should NOT feed the average.
        generated = TransactionFactory(
            user=user, category=expense_category, type=Transaction.Type.EXPENSE,
            amount=Decimal("500.00"), date=THIS_MONTH,
        )
        mark_as_recurring_generated(generated, recurring)

        client = authed_client(user)
        response = client.get("/api/forecast/", {"trailing_months": 2})
        assert Decimal(response.data["avg_monthly_expenses"]) == Decimal("200.00")


@pytest.mark.django_db
class TestRecurringOverridesProjection:
    def test_recurring_expense_lands_in_its_own_due_month(self):
        user = UserFactory()
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        expense_category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        for i in range(2):
            month = add_months(THIS_MONTH, -i)
            TransactionFactory(
                user=user, category=income_category, type=Transaction.Type.INCOME,
                amount=Decimal("2000.00"), date=month,
            )

        future_due_date = add_months(THIS_MONTH, 3)
        RecurringTransactionFactory(
            user=user,
            category=expense_category,
            type="expense",
            amount=Decimal("5000.00"),
            frequency="yearly",
            next_run_date=future_due_date,
        )

        client = authed_client(user)
        response = client.get(
            "/api/forecast/", {"trailing_months": 2, "projection_months": 6}
        )
        series = response.data["monthly_projection"]
        by_month = {row["month"]: Decimal(row["projected_net_worth"]) for row in series}

        month_before = by_month[add_months(THIS_MONTH, 2).isoformat()]
        month_of = by_month[future_due_date.isoformat()]
        month_after = by_month[add_months(THIS_MONTH, 4).isoformat()]

        # Net worth should drop by (5000 - avg_savings) more than a normal
        # month specifically in the due month, then resume the normal pace.
        avg_savings = Decimal(response.data["avg_monthly_savings"])
        assert month_of - month_before == avg_savings - Decimal("5000.00")
        assert month_after - month_of == avg_savings


@pytest.mark.django_db
class TestProjectionAndScope:
    def test_current_net_worth_reflects_history(self):
        user = UserFactory()
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        expense_category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        TransactionFactory(
            user=user, category=income_category, type=Transaction.Type.INCOME,
            amount=Decimal("5000.00"), date=THIS_MONTH,
        )
        TransactionFactory(
            user=user, category=expense_category, type=Transaction.Type.EXPENSE,
            amount=Decimal("1000.00"), date=add_months(THIS_MONTH, -1),
        )

        client = authed_client(user)
        response = client.get("/api/forecast/")
        assert Decimal(response.data["current_net_worth"]) == Decimal("4000.00")

    def test_projection_has_requested_number_of_months(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        for i in range(2):
            TransactionFactory(
                user=user, category=category, type=Transaction.Type.INCOME,
                amount=Decimal("100.00"), date=add_months(THIS_MONTH, -i),
            )

        client = authed_client(user)
        response = client.get("/api/forecast/", {"projection_months": 4})
        assert len(response.data["monthly_projection"]) == 4

    def test_non_member_cannot_scope_to_a_household(self):
        user = UserFactory()
        household = HouseholdFactory()
        client = authed_client(user)
        response = client.get("/api/forecast/", {"household": str(household.id)})
        assert response.status_code == 403

    def test_household_scope_excludes_personal_transactions(self):
        user = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=user, household=household, role=HouseholdMembership.Role.OWNER
        )
        category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        for i in range(2):
            month = add_months(THIS_MONTH, -i)
            TransactionFactory(
                user=user, category=category, type=Transaction.Type.INCOME,
                amount=Decimal("1000.00"), date=month, household=None,
            )
            TransactionFactory(
                user=user, category=category, type=Transaction.Type.INCOME,
                amount=Decimal("300.00"), date=month, household=household,
            )

        client = authed_client(user)
        response = client.get(
            "/api/forecast/", {"household": str(household.id), "trailing_months": 2}
        )
        assert Decimal(response.data["avg_monthly_income"]) == Decimal("300.00")

    def test_invalid_trailing_months_returns_400(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.get("/api/forecast/", {"trailing_months": "0"})
        assert response.status_code == 400

    def test_unauthenticated_request_is_rejected(self):
        client = APIClient()
        response = client.get("/api/forecast/")
        assert response.status_code == 401
