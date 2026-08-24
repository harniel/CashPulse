"""
Notification sweep (Section 17, hourly beat): evaluates each rule and
creates a Notification unless an unread one for the same (user, type,
entity) already exists, so repeated sweeps don't spam duplicates.

Four of the five documented types (Section 18) are implemented:
budget_exceeded/budget_approaching, recurring_due_soon, loan_payment_due,
goal_behind_pace. `unusual_expense` is deliberately deferred — unlike the
other four, the blueprint never specifies a concrete rule for it (no
threshold, no comparison basis), and inventing one here would be an
arbitrary guess rather than an implementation of something specified.
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from budgets.models import Budget
from budgets.services import compute_spent
from common.dates import add_months
from common.money import quantize
from loans.models import Loan
from loans.services import remaining_balance
from recurring_transactions.models import RecurringTransaction
from savings.models import SavingsGoal
from savings.services import is_behind_pace, total_contributed

from .models import Notification

BUDGET_APPROACHING_THRESHOLD = Decimal("80")
RECURRING_DUE_SOON_DAYS = 3
LOAN_PAYMENT_DUE_SOON_DAYS = 3


def _already_notified(user, type_, entity_id):
    return Notification.objects.filter(
        user=user, type=type_, read_at__isnull=True, payload__entity_id=str(entity_id)
    ).exists()


def _notify(user, household, type_, payload):
    Notification.objects.create(user=user, household=household, type=type_, payload=payload)


def _sweep_budgets(today):
    created = 0
    current_month = today.replace(day=1)
    for budget in Budget.objects.filter(month=current_month).select_related("category"):
        if budget.amount <= 0:
            continue
        spent = compute_spent(budget)
        utilization_pct = quantize(spent / budget.amount * 100)

        if utilization_pct >= 100:
            type_ = Notification.Type.BUDGET_EXCEEDED
        elif utilization_pct >= BUDGET_APPROACHING_THRESHOLD:
            type_ = Notification.Type.BUDGET_APPROACHING
        else:
            continue

        if _already_notified(budget.user, type_, budget.id):
            continue
        _notify(
            budget.user,
            budget.household,
            type_,
            {
                "entity_id": str(budget.id),
                "category": budget.category.name,
                "amount": str(budget.amount),
                "spent": str(spent),
                "utilization_pct": str(utilization_pct),
            },
        )
        created += 1
    return created


def _sweep_recurring(today):
    created = 0
    horizon = today + timedelta(days=RECURRING_DUE_SOON_DAYS)
    qs = RecurringTransaction.objects.filter(next_run_date__gt=today, next_run_date__lte=horizon)
    for recurring in qs:
        if _already_notified(recurring.user, Notification.Type.RECURRING_DUE_SOON, recurring.id):
            continue
        _notify(
            recurring.user,
            recurring.household,
            Notification.Type.RECURRING_DUE_SOON,
            {
                "entity_id": str(recurring.id),
                "description": recurring.description,
                "amount": str(recurring.amount),
                "due_date": recurring.next_run_date.isoformat(),
            },
        )
        created += 1
    return created


def _next_loan_payment_due_date(loan, as_of):
    due_day = min(loan.start_date.day, calendar.monthrange(as_of.year, as_of.month)[1])
    candidate = as_of.replace(day=due_day)
    if candidate < as_of:
        candidate = add_months(candidate, 1)
    return candidate


def _sweep_loans(today):
    created = 0
    horizon = today + timedelta(days=LOAN_PAYMENT_DUE_SOON_DAYS)
    for loan in Loan.objects.all():
        if remaining_balance(loan) <= 0:
            continue
        due_date = _next_loan_payment_due_date(loan, today)
        if due_date > horizon:
            continue
        if _already_notified(loan.user, Notification.Type.LOAN_PAYMENT_DUE, loan.id):
            continue
        _notify(
            loan.user,
            None,
            Notification.Type.LOAN_PAYMENT_DUE,
            {
                "entity_id": str(loan.id),
                "lender": loan.lender,
                "due_date": due_date.isoformat(),
            },
        )
        created += 1
    return created


def _sweep_goals(today):
    created = 0
    for goal in SavingsGoal.objects.all():
        if is_behind_pace(goal, as_of=today) is not True:
            continue
        if _already_notified(goal.user, Notification.Type.GOAL_BEHIND_PACE, goal.id):
            continue
        _notify(
            goal.user,
            goal.household,
            Notification.Type.GOAL_BEHIND_PACE,
            {
                "entity_id": str(goal.id),
                "name": goal.name,
                "target_amount": str(goal.target_amount),
                "total_contributed": str(total_contributed(goal)),
            },
        )
        created += 1
    return created


def sweep(today=None):
    today = today or date.today()
    return {
        "budgets": _sweep_budgets(today),
        "recurring": _sweep_recurring(today),
        "loans": _sweep_loans(today),
        "goals": _sweep_goals(today),
    }
