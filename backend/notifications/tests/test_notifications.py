import datetime
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from budgets.tests.factories import BudgetFactory
from categories.models import Category
from loans.services import log_payment
from loans.tests.factories import LoanFactory
from notifications.models import Notification
from notifications.services import _next_loan_payment_due_date, sweep
from notifications.tests.factories import NotificationFactory
from recurring_transactions.tests.factories import RecurringTransactionFactory
from savings.models import SavingsGoal
from savings.services import log_contribution
from savings.tests.factories import SavingsGoalFactory
from transactions.models import Transaction
from transactions.tests.factories import CategoryFactory, TransactionFactory
from users.tests.factories import UserFactory

TODAY = datetime.date(2026, 8, 24)


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestBudgetSweep:
    def test_exceeded_budget_creates_notification(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        budget = BudgetFactory(user=user, category=category, month=TODAY.replace(day=1), amount=Decimal("100.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("150.00"), date=TODAY,
        )

        sweep(today=TODAY)
        notification = Notification.objects.get(user=user, type=Notification.Type.BUDGET_EXCEEDED)
        assert notification.payload["entity_id"] == str(budget.id)

    def test_approaching_budget_creates_notification(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        BudgetFactory(user=user, category=category, month=TODAY.replace(day=1), amount=Decimal("100.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("85.00"), date=TODAY,
        )

        sweep(today=TODAY)
        assert Notification.objects.filter(
            user=user, type=Notification.Type.BUDGET_APPROACHING
        ).exists()
        assert not Notification.objects.filter(
            user=user, type=Notification.Type.BUDGET_EXCEEDED
        ).exists()

    def test_under_threshold_budget_creates_no_notification(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        BudgetFactory(user=user, category=category, month=TODAY.replace(day=1), amount=Decimal("100.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("10.00"), date=TODAY,
        )

        sweep(today=TODAY)
        assert not Notification.objects.filter(user=user).exists()

    def test_sweep_does_not_duplicate_an_unread_notification(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        BudgetFactory(user=user, category=category, month=TODAY.replace(day=1), amount=Decimal("100.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("150.00"), date=TODAY,
        )

        sweep(today=TODAY)
        sweep(today=TODAY)
        assert Notification.objects.filter(user=user, type=Notification.Type.BUDGET_EXCEEDED).count() == 1

    def test_sweep_creates_a_new_notification_once_the_old_one_is_read(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        BudgetFactory(user=user, category=category, month=TODAY.replace(day=1), amount=Decimal("100.00"))
        TransactionFactory(
            user=user, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("150.00"), date=TODAY,
        )

        sweep(today=TODAY)
        Notification.objects.filter(user=user).update(read_at=timezone.now())
        sweep(today=TODAY)
        assert Notification.objects.filter(user=user, type=Notification.Type.BUDGET_EXCEEDED).count() == 2


@pytest.mark.django_db
class TestRecurringSweep:
    def test_recurring_due_soon_creates_notification(self):
        recurring = RecurringTransactionFactory(next_run_date=TODAY + datetime.timedelta(days=2))
        sweep(today=TODAY)
        notification = Notification.objects.get(type=Notification.Type.RECURRING_DUE_SOON)
        assert notification.payload["entity_id"] == str(recurring.id)

    def test_recurring_far_in_the_future_creates_no_notification(self):
        RecurringTransactionFactory(next_run_date=TODAY + datetime.timedelta(days=30))
        sweep(today=TODAY)
        assert not Notification.objects.filter(type=Notification.Type.RECURRING_DUE_SOON).exists()

    def test_already_overdue_recurring_creates_no_notification(self):
        # Overdue is the generator's job (recurring_transactions), not the sweep's.
        RecurringTransactionFactory(next_run_date=TODAY - datetime.timedelta(days=1))
        sweep(today=TODAY)
        assert not Notification.objects.filter(type=Notification.Type.RECURRING_DUE_SOON).exists()


@pytest.mark.django_db
class TestLoanSweep:
    def test_next_payment_due_date_helper(self):
        assert _next_loan_payment_due_date(
            LoanFactory.build(start_date=datetime.date(2026, 1, 15)), datetime.date(2026, 8, 20)
        ) == datetime.date(2026, 9, 15)
        assert _next_loan_payment_due_date(
            LoanFactory.build(start_date=datetime.date(2026, 1, 15)), datetime.date(2026, 8, 10)
        ) == datetime.date(2026, 8, 15)

    def test_loan_due_soon_creates_notification(self):
        loan = LoanFactory(start_date=TODAY.replace(day=1) + datetime.timedelta(days=25))
        sweep(today=TODAY)
        assert Notification.objects.filter(
            type=Notification.Type.LOAN_PAYMENT_DUE, payload__entity_id=str(loan.id)
        ).exists()

    def test_paid_off_loan_creates_no_notification(self):
        loan = LoanFactory(
            principal=Decimal("100.00"), interest_rate=Decimal("0.000"), term_months=1,
            start_date=TODAY - datetime.timedelta(days=5),
        )
        log_payment(loan, date_=TODAY, amount=Decimal("100.00"), is_extra=False)
        sweep(today=TODAY)
        assert not Notification.objects.filter(type=Notification.Type.LOAN_PAYMENT_DUE).exists()


@pytest.mark.django_db
class TestGoalSweep:
    def test_behind_pace_goal_creates_notification(self):
        goal = SavingsGoalFactory(
            target_amount=Decimal("1000.00"), target_date=TODAY + datetime.timedelta(days=50)
        )
        SavingsGoal.objects.filter(id=goal.id).update(
            created_at=timezone.make_aware(
                datetime.datetime.combine(TODAY - datetime.timedelta(days=50), datetime.time())
            )
        )
        log_contribution(goal, date_=TODAY, amount=Decimal("100.00"))

        sweep(today=TODAY)
        assert Notification.objects.filter(
            type=Notification.Type.GOAL_BEHIND_PACE, payload__entity_id=str(goal.id)
        ).exists()

    def test_on_track_goal_creates_no_notification(self):
        SavingsGoalFactory(target_amount=Decimal("1000.00"), target_date=TODAY + datetime.timedelta(days=365))
        sweep(today=TODAY)
        assert not Notification.objects.filter(type=Notification.Type.GOAL_BEHIND_PACE).exists()


@pytest.mark.django_db
class TestNotificationAPI:
    def test_list_only_returns_own_notifications(self):
        user = UserFactory()
        NotificationFactory.create_batch(2, user=user)
        NotificationFactory.create_batch(3, user=UserFactory())

        client = authed_client(user)
        response = client.get("/api/notifications/")
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_patch_marks_read_regardless_of_body(self):
        user = UserFactory()
        notification = NotificationFactory(user=user)
        assert notification.read_at is None

        client = authed_client(user)
        response = client.patch(f"/api/notifications/{notification.id}/", {})
        assert response.status_code == 200
        notification.refresh_from_db()
        assert notification.read_at is not None

    def test_cannot_mark_another_users_notification_read(self):
        notification = NotificationFactory()
        client = authed_client(UserFactory())
        response = client.patch(f"/api/notifications/{notification.id}/", {})
        assert response.status_code == 404
        notification.refresh_from_db()
        assert notification.read_at is None

    def test_unauthenticated_request_is_rejected(self):
        client = APIClient()
        response = client.get("/api/notifications/")
        assert response.status_code == 401
