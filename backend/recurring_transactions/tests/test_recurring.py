import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import AccountFactory
from categories.models import Category
from common.dates import advance_date
from households.models import HouseholdMembership
from households.tests.factories import HouseholdFactory, HouseholdMembershipFactory
from recurring_transactions.models import GeneratedOccurrence, RecurringTransaction
from recurring_transactions.services import generate_due_occurrences, skip_next
from recurring_transactions.tests.factories import RecurringTransactionFactory
from transactions.models import Transaction
from transactions.tests.factories import CategoryFactory
from users.tests.factories import UserFactory

TODAY = datetime.date.today()


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestRecurringCreate:
    def test_create_monthly_expense(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/recurring-transactions/",
            {
                "account": str(account.id),
                "category": str(category.id),
                "type": "expense",
                "amount": "1200.00",
                "frequency": "monthly",
                "next_run_date": TODAY.isoformat(),
            },
        )
        assert response.status_code == 201
        recurring = RecurringTransaction.objects.get(id=response.data["id"])
        assert recurring.user_id == user.id
        assert recurring.currency == account.currency

    def test_create_transfer(self):
        user = UserFactory()
        source = AccountFactory(user=user)
        destination = AccountFactory(user=user)
        client = authed_client(user)

        response = client.post(
            "/api/recurring-transactions/",
            {
                "account": str(source.id),
                "to_account": str(destination.id),
                "type": "transfer",
                "amount": "500.00",
                "frequency": "monthly",
                "next_run_date": TODAY.isoformat(),
            },
        )
        assert response.status_code == 201

    def test_amount_must_be_positive(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/recurring-transactions/",
            {
                "account": str(account.id),
                "category": str(category.id),
                "type": "expense",
                "amount": "0.00",
                "frequency": "monthly",
                "next_run_date": TODAY.isoformat(),
            },
        )
        assert response.status_code == 400

    def test_expense_requires_category(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        response = client.post(
            "/api/recurring-transactions/",
            {
                "account": str(account.id),
                "type": "expense",
                "amount": "10.00",
                "frequency": "weekly",
                "next_run_date": TODAY.isoformat(),
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
            "/api/recurring-transactions/",
            {
                "account": str(source.id),
                "to_account": str(destination.id),
                "category": str(category.id),
                "type": "transfer",
                "amount": "10.00",
                "frequency": "monthly",
                "next_run_date": TODAY.isoformat(),
            },
        )
        assert response.status_code == 400

    def test_end_date_before_next_run_date_is_rejected(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/recurring-transactions/",
            {
                "account": str(account.id),
                "category": str(category.id),
                "type": "expense",
                "amount": "10.00",
                "frequency": "monthly",
                "next_run_date": TODAY.isoformat(),
                "end_date": (TODAY - datetime.timedelta(days=1)).isoformat(),
            },
        )
        assert response.status_code == 400

    def test_cannot_use_another_users_account(self):
        user = UserFactory()
        other_account = AccountFactory(user=UserFactory())
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/recurring-transactions/",
            {
                "account": str(other_account.id),
                "category": str(category.id),
                "type": "expense",
                "amount": "10.00",
                "frequency": "monthly",
                "next_run_date": TODAY.isoformat(),
            },
        )
        assert response.status_code == 400

    def test_shared_recurring_requires_membership(self):
        user = UserFactory()
        household = HouseholdFactory()
        account = AccountFactory(user=user)
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/recurring-transactions/",
            {
                "account": str(account.id),
                "category": str(category.id),
                "household": str(household.id),
                "type": "expense",
                "amount": "10.00",
                "frequency": "monthly",
                "next_run_date": TODAY.isoformat(),
            },
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestSkipNext:
    def test_skip_next_advances_without_generating(self):
        user = UserFactory()
        recurring = RecurringTransactionFactory(
            user=user, frequency=RecurringTransaction.Frequency.MONTHLY, next_run_date=TODAY
        )
        client = authed_client(user)

        response = client.post(f"/api/recurring-transactions/{recurring.id}/skip-next/")
        assert response.status_code == 200
        recurring.refresh_from_db()
        assert recurring.next_run_date > TODAY
        assert not GeneratedOccurrence.objects.filter(recurring=recurring).exists()
        assert not Transaction.objects.filter(user=user).exists()


class TestAdvanceDate:
    def test_weekly(self):
        assert advance_date(datetime.date(2026, 1, 1), "weekly") == datetime.date(2026, 1, 8)

    def test_biweekly(self):
        assert advance_date(datetime.date(2026, 1, 1), "biweekly") == datetime.date(2026, 1, 15)

    def test_monthly_clamps_at_month_end(self):
        assert advance_date(datetime.date(2026, 1, 31), "monthly") == datetime.date(2026, 2, 28)

    def test_monthly_normal(self):
        assert advance_date(datetime.date(2026, 3, 15), "monthly") == datetime.date(2026, 4, 15)

    def test_yearly_clamps_leap_day(self):
        assert advance_date(datetime.date(2024, 2, 29), "yearly") == datetime.date(2025, 2, 28)

    def test_yearly_normal(self):
        assert advance_date(datetime.date(2026, 6, 1), "yearly") == datetime.date(2027, 6, 1)


@pytest.mark.django_db
class TestGenerateDueOccurrences:
    def test_generates_when_due(self):
        recurring = RecurringTransactionFactory(
            amount=Decimal("75.00"), frequency=RecurringTransaction.Frequency.MONTHLY, next_run_date=TODAY
        )
        generated = generate_due_occurrences(today=TODAY)

        assert len(generated) == 1
        transaction = generated[0]
        assert transaction.amount == Decimal("75.00")
        assert transaction.user_id == recurring.user_id
        assert GeneratedOccurrence.objects.filter(recurring=recurring, due_date=TODAY).exists()
        recurring.refresh_from_db()
        assert recurring.next_run_date > TODAY

    def test_does_not_generate_before_due(self):
        RecurringTransactionFactory(next_run_date=TODAY + datetime.timedelta(days=5))
        generated = generate_due_occurrences(today=TODAY)
        assert generated == []

    def test_sequential_double_run_does_not_duplicate(self):
        RecurringTransactionFactory(
            frequency=RecurringTransaction.Frequency.MONTHLY, next_run_date=TODAY
        )
        first = generate_due_occurrences(today=TODAY)
        second = generate_due_occurrences(today=TODAY)

        assert len(first) == 1
        assert len(second) == 0
        assert Transaction.objects.count() == 1

    def test_pre_existing_occurrence_is_not_duplicated(self):
        # Simulates a retried/duplicated task run hitting the same
        # due_date: the unique(recurring, due_date) constraint is what's
        # actually under test here, not just the next_run_date advance.
        recurring = RecurringTransactionFactory(
            frequency=RecurringTransaction.Frequency.MONTHLY, next_run_date=TODAY
        )
        existing_transaction = Transaction.objects.create(
            user=recurring.user,
            account=recurring.account,
            category=recurring.category,
            type=recurring.type,
            amount=recurring.amount,
            currency=recurring.currency,
            date=TODAY,
            description="already posted",
        )
        GeneratedOccurrence.objects.create(
            recurring=recurring, due_date=TODAY, transaction=existing_transaction
        )

        generated = generate_due_occurrences(today=TODAY)

        assert generated == []
        assert Transaction.objects.count() == 1
        assert GeneratedOccurrence.objects.filter(recurring=recurring).count() == 1

    def test_catches_up_multiple_missed_periods(self):
        overdue_start = TODAY - datetime.timedelta(weeks=3)
        recurring = RecurringTransactionFactory(
            frequency=RecurringTransaction.Frequency.WEEKLY, next_run_date=overdue_start
        )
        generated = generate_due_occurrences(today=TODAY)

        assert len(generated) == 4  # weeks 0, 1, 2, 3 back from today
        due_dates = set(
            GeneratedOccurrence.objects.filter(recurring=recurring).values_list("due_date", flat=True)
        )
        assert due_dates == {
            overdue_start,
            overdue_start + datetime.timedelta(weeks=1),
            overdue_start + datetime.timedelta(weeks=2),
            overdue_start + datetime.timedelta(weeks=3),
        }

    def test_stops_generating_past_end_date(self):
        recurring = RecurringTransactionFactory(
            frequency=RecurringTransaction.Frequency.WEEKLY,
            next_run_date=TODAY - datetime.timedelta(weeks=2),
            end_date=TODAY - datetime.timedelta(weeks=1),
        )
        generated = generate_due_occurrences(today=TODAY)

        assert len(generated) == 2  # the overdue week and the end_date week only
        recurring.refresh_from_db()
        assert recurring.next_run_date > recurring.end_date

    def test_shared_recurring_generates_shared_transaction(self):
        user = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=user, household=household, role=HouseholdMembership.Role.OWNER
        )
        RecurringTransactionFactory(user=user, household=household, next_run_date=TODAY)
        generated = generate_due_occurrences(today=TODAY)

        assert len(generated) == 1
        assert generated[0].household_id == household.id


@pytest.mark.django_db
class TestSkipNextService:
    def test_skip_next_service_advances_date(self):
        recurring = RecurringTransactionFactory(
            frequency=RecurringTransaction.Frequency.WEEKLY, next_run_date=TODAY
        )
        skip_next(recurring)
        recurring.refresh_from_db()
        assert recurring.next_run_date == TODAY + datetime.timedelta(days=7)
