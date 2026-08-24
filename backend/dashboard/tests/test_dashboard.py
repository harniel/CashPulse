import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from budgets.tests.factories import BudgetFactory
from categories.models import Category
from households.models import HouseholdMembership
from households.tests.factories import HouseholdFactory, HouseholdMembershipFactory
from transactions.models import Transaction
from transactions.tests.factories import CategoryFactory, TransactionFactory
from users.tests.factories import UserFactory

TODAY = datetime.date.today()
THIS_MONTH = TODAY.replace(day=1)


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestDashboardSummaryAuth:
    def test_unauthenticated_request_is_rejected(self):
        client = APIClient()
        response = client.get("/api/dashboard/summary/")
        assert response.status_code == 401

    def test_non_member_cannot_scope_to_a_household(self):
        user = UserFactory()
        household = HouseholdFactory()
        client = authed_client(user)
        response = client.get("/api/dashboard/summary/", {"household": str(household.id)})
        assert response.status_code == 403

    def test_invalid_household_id_is_a_clean_400(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.get("/api/dashboard/summary/", {"household": "not-a-uuid"})
        assert response.status_code == 400


@pytest.mark.django_db
class TestDashboardTotals:
    def test_personal_net_cash_flow_and_savings_rate(self):
        user = UserFactory()
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        expense_category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        TransactionFactory(
            user=user, category=income_category, type=Transaction.Type.INCOME,
            amount=Decimal("1000.00"), date=TODAY,
        )
        TransactionFactory(
            user=user, category=expense_category, type=Transaction.Type.EXPENSE,
            amount=Decimal("400.00"), date=TODAY,
        )

        client = authed_client(user)
        response = client.get("/api/dashboard/summary/")
        assert response.status_code == 200
        assert Decimal(response.data["net_cash_flow"]) == Decimal("600.00")
        assert Decimal(response.data["savings_rate_pct"]) == Decimal("60.00")
        assert Decimal(response.data["net_worth"]) == Decimal("600.00")

    def test_savings_rate_is_null_with_no_income(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.get("/api/dashboard/summary/")
        assert response.status_code == 200
        assert response.data["savings_rate_pct"] is None

    def test_household_scope_excludes_personal_transactions(self):
        user = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=user, household=household, role=HouseholdMembership.Role.OWNER
        )
        expense_category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        TransactionFactory(
            user=user, category=expense_category, type=Transaction.Type.EXPENSE,
            amount=Decimal("100.00"), date=TODAY, household=None,
        )
        TransactionFactory(
            user=user, category=expense_category, type=Transaction.Type.EXPENSE,
            amount=Decimal("50.00"), date=TODAY, household=household,
        )

        client = authed_client(user)
        response = client.get("/api/dashboard/summary/", {"household": str(household.id)})
        assert response.status_code == 200
        assert Decimal(response.data["net_cash_flow"]) == Decimal("-50.00")
        assert response.data["scope"]["household"] == household.id


@pytest.mark.django_db
class TestDashboardCharts:
    def test_cash_flow_by_month_has_six_entries_ending_this_month(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.get("/api/dashboard/summary/")
        series = response.data["charts"]["cash_flow_by_month"]
        assert len(series) == 6
        assert series[-1]["month"] == THIS_MONTH.isoformat()

    def test_spending_by_category_aggregates_expenses(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE, name="Groceries")
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("30.00"), date=TODAY,
        )
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("20.00"), date=TODAY,
        )

        client = authed_client(user)
        response = client.get("/api/dashboard/summary/")
        rows = response.data["charts"]["spending_by_category"]
        assert len(rows) == 1
        assert rows[0]["category"] == "Groceries"
        assert Decimal(rows[0]["amount"]) == Decimal("50.00")

    def test_net_worth_by_month_reflects_cumulative_income_minus_expense(self):
        user = UserFactory()
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        last_month = (THIS_MONTH - datetime.timedelta(days=1)).replace(day=1)
        TransactionFactory(
            user=user, category=income_category, type=Transaction.Type.INCOME,
            amount=Decimal("200.00"), date=last_month,
        )

        client = authed_client(user)
        response = client.get("/api/dashboard/summary/")
        series = response.data["charts"]["net_worth_by_month"]
        by_month = {row["month"]: Decimal(row["net_worth"]) for row in series}
        assert by_month[THIS_MONTH.isoformat()] == Decimal("200.00")

    def test_budget_utilization_matches_budget_spent(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        BudgetFactory(user=user, category=category, month=THIS_MONTH, amount=Decimal("100.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("60.00"), date=TODAY,
        )

        client = authed_client(user)
        response = client.get("/api/dashboard/summary/")
        rows = response.data["charts"]["budget_utilization"]
        assert len(rows) == 1
        assert Decimal(rows[0]["spent"]) == Decimal("60.00")
        assert Decimal(rows[0]["utilization_pct"]) == Decimal("60.00")


@pytest.mark.django_db
class TestDashboardInsights:
    def test_budget_exceeded_insight(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE, name="Fun")
        BudgetFactory(user=user, category=category, month=THIS_MONTH, amount=Decimal("100.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("150.00"), date=TODAY,
        )

        client = authed_client(user)
        response = client.get("/api/dashboard/summary/")
        types = [i["type"] for i in response.data["insights"]]
        assert "budget_exceeded" in types

    def test_budget_approaching_insight(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE, name="Fun")
        BudgetFactory(user=user, category=category, month=THIS_MONTH, amount=Decimal("100.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("85.00"), date=TODAY,
        )

        client = authed_client(user)
        response = client.get("/api/dashboard/summary/")
        types = [i["type"] for i in response.data["insights"]]
        assert "budget_approaching" in types
        assert "budget_exceeded" not in types

    def test_no_insight_when_under_threshold(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        BudgetFactory(user=user, category=category, month=THIS_MONTH, amount=Decimal("100.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("10.00"), date=TODAY,
        )

        client = authed_client(user)
        response = client.get("/api/dashboard/summary/")
        assert response.data["insights"] == []

    def test_negative_cash_flow_insight(self):
        user = UserFactory()
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        expense_category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        TransactionFactory(
            user=user, category=income_category, type=Transaction.Type.INCOME,
            amount=Decimal("100.00"), date=TODAY,
        )
        TransactionFactory(
            user=user, category=expense_category, type=Transaction.Type.EXPENSE,
            amount=Decimal("300.00"), date=TODAY,
        )

        client = authed_client(user)
        response = client.get("/api/dashboard/summary/")
        types = [i["type"] for i in response.data["insights"]]
        assert "negative_cash_flow" in types
