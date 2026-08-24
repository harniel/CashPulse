"""
Business logic for recurring transactions: authorization (mirrors
transactions/services.py) plus the generation engine itself (Section 17).
The engine is plain Python, deliberately independent of Celery — tasks.py
is a one-line wrapper so this can be unit-tested and run from a management
command without a broker.
"""

from datetime import date

from django.db import IntegrityError
from django.db import transaction as db_transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.dates import advance_date
from households.models import HouseholdMembership
from transactions.models import Transaction

from .models import GeneratedOccurrence, RecurringTransaction


def _validate_account_ownership(owner, account, field_name="account"):
    if account is not None and account.user_id != owner.id:
        raise ValidationError({field_name: "You don't have access to that account."})


def _validate_household_membership(user, household):
    if household is None:
        return
    if not HouseholdMembership.objects.filter(user=user, household=household).exists():
        raise PermissionDenied("You're not a member of that household.")


def create_recurring(user, **data):
    account = data.get("account")
    to_account = data.get("to_account")
    household = data.get("household")

    _validate_account_ownership(user, account)
    _validate_account_ownership(user, to_account, field_name="to_account")
    _validate_household_membership(user, household)

    data.setdefault("currency", account.currency if account else "PHP")

    recurring = RecurringTransaction(user=user, **data)
    recurring.save()
    return recurring


def update_recurring(recurring, **data):
    owner = recurring.user
    account = data.get("account", recurring.account)
    to_account = data.get("to_account", recurring.to_account)
    household = data.get("household", recurring.household)

    _validate_account_ownership(owner, account)
    _validate_account_ownership(owner, to_account, field_name="to_account")
    _validate_household_membership(owner, household)

    for field, value in data.items():
        setattr(recurring, field, value)
    recurring.save()
    return recurring


def skip_next(recurring):
    recurring.next_run_date = advance_date(recurring.next_run_date, recurring.frequency)
    recurring.save(update_fields=["next_run_date"])
    return recurring


def generate_due_occurrences(today=None):
    """
    For every RecurringTransaction due (next_run_date <= today), post the
    Transaction(s) it owes — looping to catch up on any missed periods if
    the job hasn't run in a while — then advance next_run_date past today.
    Each post is wrapped in its own atomic block guarded by
    GeneratedOccurrence's unique(recurring, due_date) constraint, so a
    retried/duplicated run for a due_date already posted hits an
    IntegrityError that's caught and ignored rather than double-posting.
    """
    if today is None:
        today = date.today()

    generated = []
    for recurring in RecurringTransaction.objects.filter(next_run_date__lte=today):
        due_date = recurring.next_run_date
        while due_date <= today and (
            recurring.end_date is None or due_date <= recurring.end_date
        ):
            try:
                with db_transaction.atomic():
                    transaction = Transaction.objects.create(
                        user=recurring.user,
                        household=recurring.household,
                        account=recurring.account,
                        to_account=recurring.to_account,
                        category=recurring.category,
                        type=recurring.type,
                        amount=recurring.amount,
                        currency=recurring.currency,
                        date=due_date,
                        description=recurring.description,
                        notes=recurring.notes,
                    )
                    GeneratedOccurrence.objects.create(
                        recurring=recurring, due_date=due_date, transaction=transaction
                    )
                generated.append(transaction)
            except IntegrityError:
                pass
            due_date = advance_date(due_date, recurring.frequency)

        recurring.next_run_date = due_date
        recurring.save(update_fields=["next_run_date"])

    return generated
