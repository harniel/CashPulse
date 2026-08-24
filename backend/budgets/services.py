"""
Business logic for budgets — category/household authorization plus the
spent/remaining/utilization/daily-recommended-spend calculations, all
computed live from the transaction ledger rather than cached on the row
(Section 14: "aggregate, don't store" applies here the same way it does
to Account.balance).
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit import services as audit
from common.money import quantize
from households.models import HouseholdMembership

from .models import Budget


def _validate_household_membership(user, household):
    if household is None:
        return
    if not HouseholdMembership.objects.filter(user=user, household=household).exists():
        raise PermissionDenied("You're not a member of that household.")


def _validate_category_access(user, category):
    if category is None or category.is_system:
        return
    if category.user_id != user.id:
        raise ValidationError({"category": "You don't have access to that category."})


def create_budget(user, **data):
    _validate_household_membership(user, data.get("household"))
    _validate_category_access(user, data.get("category"))
    budget = Budget(user=user, **data)
    budget.save()
    audit.log(
        user=user,
        household=budget.household,
        action="create",
        entity_type="Budget",
        entity_id=budget.id,
        metadata=audit.full_snapshot(budget),
    )
    return budget


def update_budget(budget, actor, **data):
    household = data.get("household", budget.household)
    category = data.get("category", budget.category)
    _validate_household_membership(budget.user, household)
    _validate_category_access(budget.user, category)

    diff = audit.field_diff(budget, data)
    for field, value in data.items():
        setattr(budget, field, value)
    budget.save()
    if diff:
        audit.log(
            user=actor,
            household=budget.household,
            action="update",
            entity_type="Budget",
            entity_id=budget.id,
            metadata=diff,
        )
    return budget


def delete_budget(budget, actor):
    audit.log(
        user=actor,
        household=budget.household,
        action="delete",
        entity_type="Budget",
        entity_id=budget.id,
        metadata=audit.full_snapshot(budget),
    )
    budget.delete()


def _month_bounds(month):
    last_day = calendar.monthrange(month.year, month.month)[1]
    return month, date(month.year, month.month, last_day)


def compute_spent(budget):
    from transactions.models import Transaction

    start, end = _month_bounds(budget.month)
    qs = Transaction.objects.filter(
        category=budget.category,
        type=Transaction.Type.EXPENSE,
        date__gte=start,
        date__lte=end,
    )
    if budget.household_id:
        qs = qs.filter(household_id=budget.household_id)
    else:
        qs = qs.filter(user_id=budget.user_id, household__isnull=True)
    return qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")


def daily_recommended_spend(budget, spent=None):
    if spent is None:
        spent = compute_spent(budget)
    remaining = budget.amount - spent
    if remaining <= 0:
        return Decimal("0.00")

    start, end = _month_bounds(budget.month)
    today = date.today()
    if today > end:
        return None  # this budget's month is already over
    days_left = (end - max(today, start)).days + 1
    return quantize(remaining / days_left)


def budget_history(budget, months=6):
    qs = Budget.objects.filter(category=budget.category, month__lt=budget.month).order_by(
        "-month"
    )
    if budget.household_id:
        qs = qs.filter(household_id=budget.household_id)
    else:
        qs = qs.filter(user_id=budget.user_id, household__isnull=True)
    return qs[:months]
