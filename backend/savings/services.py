"""
Business logic for savings goals: household authorization (mirrors
transactions/budgets/services.py) plus progress/pace calculations, all
computed live from SavingsContribution rows — same "aggregate, don't
store" pattern as Account.balance, Budget.spent, Loan.remaining_balance.
"""

from datetime import date as date_cls
from decimal import Decimal

from django.db.models import Sum
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.money import quantize
from households.models import HouseholdMembership

from .models import SavingsContribution, SavingsGoal

MIN_MONTHS_FOR_REQUIRED_CONTRIBUTION = 1


def _validate_household_membership(user, household):
    if household is None:
        return
    if not HouseholdMembership.objects.filter(user=user, household=household).exists():
        raise PermissionDenied("You're not a member of that household.")


def create_goal(user, **data):
    _validate_household_membership(user, data.get("household"))
    goal = SavingsGoal(user=user, **data)
    goal.save()
    return goal


def update_goal(goal, **data):
    household = data.get("household", goal.household)
    _validate_household_membership(goal.user, household)
    for field, value in data.items():
        setattr(goal, field, value)
    goal.save()
    return goal


def total_contributed(goal):
    return goal.contributions.aggregate(total=Sum("amount"))["total"] or Decimal("0")


def progress_pct(goal):
    if goal.target_amount == 0:
        return None
    return quantize(min(total_contributed(goal) / goal.target_amount * 100, Decimal("999.99")))


def _months_remaining(from_date, target_date):
    """Whole months between from_date and target_date, floor-rounded,
    at least 1 — a rough guide for "how much per month," not a precise
    day-count amortization (same approximate spirit as Budget's
    daily_recommended_spend and the blueprint's forecasting design)."""
    if target_date <= from_date:
        return 0
    months = (target_date.year - from_date.year) * 12 + (target_date.month - from_date.month)
    if target_date.day < from_date.day:
        months -= 1
    return max(months, MIN_MONTHS_FOR_REQUIRED_CONTRIBUTION)


def required_monthly_contribution(goal, as_of=None):
    as_of = as_of or date_cls.today()
    remaining_amount = goal.target_amount - total_contributed(goal)
    if remaining_amount <= 0:
        return Decimal("0.00")
    if goal.target_date <= as_of:
        return None  # past the target date — a monthly rate isn't meaningful anymore
    months = _months_remaining(as_of, goal.target_date)
    return quantize(remaining_amount / months)


def is_behind_pace(goal, as_of=None):
    """
    Linear pacing from the goal's creation to its target_date: by `as_of`,
    the fraction of elapsed time should roughly match the fraction of
    target_amount contributed. True only once there's actually elapsed
    time and a due date to compare against — not on day one, and not once
    the goal's already been met.
    """
    as_of = as_of or date_cls.today()
    if total_contributed(goal) >= goal.target_amount:
        return False

    start = goal.created_at.date()
    total_days = (goal.target_date - start).days
    if total_days <= 0:
        return None  # target_date at/before creation — pacing is undefined

    elapsed_days = (as_of - start).days
    if elapsed_days <= 0:
        return False
    elapsed_days = min(elapsed_days, total_days)

    expected = quantize(goal.target_amount * Decimal(elapsed_days) / Decimal(total_days))
    return total_contributed(goal) < expected


def log_contribution(goal, date_, amount):
    if amount <= 0:
        raise ValidationError({"amount": "Amount must be greater than zero."})
    if date_ < goal.created_at.date():
        raise ValidationError({"date": "Can't be before the goal was created."})

    return SavingsContribution.objects.create(goal=goal, date=date_, amount=amount)
