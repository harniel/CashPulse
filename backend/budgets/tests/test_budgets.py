import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from budgets.models import Budget
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
class TestBudgetCreate:
    def test_create_personal_budget(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/budgets/",
            {"category": str(category.id), "month": THIS_MONTH.isoformat(), "amount": "500.00"},
        )
        assert response.status_code == 201
        budget = Budget.objects.get(id=response.data["id"])
        assert budget.user_id == user.id
        assert budget.household_id is None

    def test_month_is_normalized_to_first_of_month(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/budgets/",
            {"category": str(category.id), "month": "2026-08-15", "amount": "500.00"},
        )
        assert response.status_code == 201
        budget = Budget.objects.get(id=response.data["id"])
        assert budget.month == datetime.date(2026, 8, 1)

    def test_create_shared_budget_requires_membership(self):
        user = UserFactory()
        household = HouseholdFactory()  # not a member
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/budgets/",
            {
                "category": str(category.id),
                "household": str(household.id),
                "month": THIS_MONTH.isoformat(),
                "amount": "500.00",
            },
        )
        assert response.status_code == 403

    def test_create_shared_budget_as_member(self):
        user = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=user, household=household, role=HouseholdMembership.Role.OWNER
        )
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/budgets/",
            {
                "category": str(category.id),
                "household": str(household.id),
                "month": THIS_MONTH.isoformat(),
                "amount": "500.00",
            },
        )
        assert response.status_code == 201

    def test_amount_must_be_positive(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/budgets/",
            {"category": str(category.id), "month": THIS_MONTH.isoformat(), "amount": "0.00"},
        )
        assert response.status_code == 400

    def test_cannot_use_another_users_category(self):
        user = UserFactory()
        other_category = CategoryFactory(user=UserFactory(), kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/budgets/",
            {
                "category": str(other_category.id),
                "month": THIS_MONTH.isoformat(),
                "amount": "500.00",
            },
        )
        assert response.status_code == 400

    def test_duplicate_personal_budget_same_category_month_is_rejected(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        BudgetFactory(user=user, category=category, month=THIS_MONTH)
        client = authed_client(user)

        response = client.post(
            "/api/budgets/",
            {"category": str(category.id), "month": THIS_MONTH.isoformat(), "amount": "300.00"},
        )
        assert response.status_code == 400

    def test_duplicate_shared_budget_same_household_category_month_is_rejected(self):
        owner = UserFactory()
        other_member = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=owner, household=household, role=HouseholdMembership.Role.OWNER
        )
        HouseholdMembershipFactory(
            user=other_member, household=household, role=HouseholdMembership.Role.MEMBER
        )
        category = CategoryFactory(user=owner, kind=Category.Kind.EXPENSE)
        BudgetFactory(user=owner, household=household, category=category, month=THIS_MONTH)

        client = authed_client(other_member)
        response = client.post(
            "/api/budgets/",
            {
                "category": str(category.id),
                "household": str(household.id),
                "month": THIS_MONTH.isoformat(),
                "amount": "300.00",
            },
        )
        assert response.status_code == 400

    def test_personal_and_shared_budgets_for_same_category_month_can_coexist(self):
        user = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=user, household=household, role=HouseholdMembership.Role.OWNER
        )
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        BudgetFactory(user=user, category=category, month=THIS_MONTH, household=None)

        client = authed_client(user)
        response = client.post(
            "/api/budgets/",
            {
                "category": str(category.id),
                "household": str(household.id),
                "month": THIS_MONTH.isoformat(),
                "amount": "300.00",
            },
        )
        assert response.status_code == 201


@pytest.mark.django_db
class TestBudgetComputedFields:
    def test_spent_remaining_and_utilization(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        budget = BudgetFactory(user=user, category=category, month=THIS_MONTH, amount=Decimal("500.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("150.00"), date=THIS_MONTH,
        )
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("50.00"), date=THIS_MONTH,
        )

        client = authed_client(user)
        response = client.get(f"/api/budgets/{budget.id}/")
        assert response.status_code == 200
        assert Decimal(response.data["spent"]) == Decimal("200.00")
        assert Decimal(response.data["remaining"]) == Decimal("300.00")
        assert Decimal(response.data["utilization_pct"]) == Decimal("40.00")

    def test_income_transactions_do_not_count_as_spent(self):
        user = UserFactory()
        expense_category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        income_category = CategoryFactory(user=user, kind=Category.Kind.INCOME)
        budget = BudgetFactory(user=user, category=expense_category, month=THIS_MONTH)
        TransactionFactory(
            user=user, category=income_category, type=Transaction.Type.INCOME,
            amount=Decimal("1000.00"), date=THIS_MONTH,
        )

        client = authed_client(user)
        response = client.get(f"/api/budgets/{budget.id}/")
        assert Decimal(response.data["spent"]) == Decimal("0")

    def test_daily_recommended_spend_is_null_for_a_past_month(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        past_month = (THIS_MONTH.replace(day=1) - datetime.timedelta(days=60)).replace(day=1)
        budget = BudgetFactory(user=user, category=category, month=past_month)

        client = authed_client(user)
        response = client.get(f"/api/budgets/{budget.id}/")
        assert response.data["daily_recommended_spend"] is None

    def test_daily_recommended_spend_is_zero_when_over_budget(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        budget = BudgetFactory(user=user, category=category, month=THIS_MONTH, amount=Decimal("100.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("150.00"), date=THIS_MONTH,
        )

        client = authed_client(user)
        response = client.get(f"/api/budgets/{budget.id}/")
        assert Decimal(response.data["daily_recommended_spend"]) == Decimal("0.00")


@pytest.mark.django_db
class TestBudgetFilterAndPerformance:
    def test_filter_by_month(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        BudgetFactory(user=user, category=category, month=THIS_MONTH)
        BudgetFactory(
            user=user,
            category=CategoryFactory(user=user, kind=Category.Kind.EXPENSE),
            month=datetime.date(2020, 1, 1),
        )

        client = authed_client(user)
        response = client.get("/api/budgets/", {"month": THIS_MONTH.strftime("%Y-%m")})
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_performance_returns_prior_months_for_same_category(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        last_month = (THIS_MONTH - datetime.timedelta(days=1)).replace(day=1)
        older = (last_month - datetime.timedelta(days=1)).replace(day=1)
        BudgetFactory(user=user, category=category, month=older, amount=Decimal("400.00"))
        BudgetFactory(user=user, category=category, month=last_month, amount=Decimal("450.00"))
        current = BudgetFactory(user=user, category=category, month=THIS_MONTH, amount=Decimal("500.00"))

        client = authed_client(user)
        response = client.get(f"/api/budgets/{current.id}/performance/")
        assert response.status_code == 200
        assert len(response.data) == 2
        assert response.data[0]["month"] == last_month.isoformat()


@pytest.mark.django_db
class TestBudgetIsolation:
    def test_cannot_retrieve_another_users_personal_budget(self):
        budget = BudgetFactory()
        client = authed_client(UserFactory())
        response = client.get(f"/api/budgets/{budget.id}/")
        assert response.status_code == 404

    def test_shared_budget_visible_to_other_household_member(self):
        owner = UserFactory()
        other_member = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=owner, household=household, role=HouseholdMembership.Role.OWNER
        )
        HouseholdMembershipFactory(
            user=other_member, household=household, role=HouseholdMembership.Role.MEMBER
        )
        category = CategoryFactory(user=owner, kind=Category.Kind.EXPENSE)
        budget = BudgetFactory(user=owner, household=household, category=category, month=THIS_MONTH)

        client = authed_client(other_member)
        response = client.get(f"/api/budgets/{budget.id}/")
        assert response.status_code == 200
