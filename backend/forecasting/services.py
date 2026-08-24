"""
Forecasting engine (Section 15): trailing-N-month simple moving average
of income/expense, excluding transfers, projected forward. Deliberately
a bounded, explained approximation, not a guarantee — every response
carries the assumptions (trailing_months, the averages themselves) rather
than hiding them behind a single opaque number.

Recurring transactions are handled specially: their known future amounts
override the average for the months they land in, rather than being
counted twice (once inside the trailing average from past occurrences,
again via a naive flat projection). This is done by excluding
recurring-attributable transactions (identified via the reverse
`generated_occurrence` link) from the average, then simulating each
still-active RecurringTransaction forward explicitly and adding its
exact contribution to the specific month it falls in.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

from common.dates import add_months, advance_date
from common.money import quantize
from households.services import resolve_household  # noqa: F401
from recurring_transactions.models import RecurringTransaction
from transactions.models import Transaction

DEFAULT_TRAILING_MONTHS = 6
DEFAULT_PROJECTION_MONTHS = 12
MIN_MONTHS_OF_HISTORY = 2


def _scoped_transactions(user, household):
    if household is not None:
        return Transaction.objects.filter(household=household)
    return Transaction.objects.filter(user=user, household__isnull=True)


def _scoped_recurring(user, household):
    if household is not None:
        return RecurringTransaction.objects.filter(household=household)
    return RecurringTransaction.objects.filter(user=user, household__isnull=True)


def _months_with_history(user, household, trailing_months):
    """Distinct calendar months, within the trailing window, that have at
    least one non-transfer transaction — backs the "fewer than 2 months
    of history" edge case (Section 15) so a single lucky data point can't
    masquerade as a trend."""
    current_month = date.today().replace(day=1)
    earliest = add_months(current_month, -(trailing_months - 1))
    dates = (
        _scoped_transactions(user, household)
        .exclude(type=Transaction.Type.TRANSFER)
        .filter(date__gte=earliest)
        .values_list("date", flat=True)
    )
    return {d.replace(day=1) for d in dates}


def trailing_average(user, household, trailing_months=DEFAULT_TRAILING_MONTHS):
    """
    Average monthly income/expense over the trailing window, counting
    only *non*-recurring-attributable transactions — see module
    docstring for why recurring is excluded here and simulated forward
    separately instead.
    """
    current_month = date.today().replace(day=1)
    earliest = add_months(current_month, -(trailing_months - 1))

    totals = (
        _scoped_transactions(user, household)
        .exclude(type=Transaction.Type.TRANSFER)
        .filter(date__gte=earliest, generated_occurrence__isnull=True)
        .aggregate(
            income=Sum("amount", filter=Q(type=Transaction.Type.INCOME)),
            expense=Sum("amount", filter=Q(type=Transaction.Type.EXPENSE)),
        )
    )
    income = (totals["income"] or Decimal("0")) / trailing_months
    expense = (totals["expense"] or Decimal("0")) / trailing_months
    return quantize(income), quantize(expense)


def _recurring_contribution_by_month(user, household, projection_months):
    """Simulate every still-active recurring transaction in scope forward
    from its own next_run_date, bucketing each occurrence's net-worth
    effect (income +, expense -, transfer 0 — nets to zero across a
    user's own accounts, same as Section 15/dashboard) into the calendar
    month it falls in."""
    current_month = date.today().replace(day=1)
    horizon_end = add_months(current_month, projection_months - 1)
    contributions = {add_months(current_month, i): Decimal("0") for i in range(projection_months)}

    for recurring in _scoped_recurring(user, household):
        due_date = recurring.next_run_date
        while due_date <= horizon_end:
            if recurring.end_date is not None and due_date > recurring.end_date:
                break
            month_bucket = due_date.replace(day=1)
            if month_bucket in contributions:
                if recurring.type == RecurringTransaction.Type.INCOME:
                    contributions[month_bucket] += recurring.amount
                elif recurring.type == RecurringTransaction.Type.EXPENSE:
                    contributions[month_bucket] -= recurring.amount
            due_date = advance_date(due_date, recurring.frequency)

    return contributions


def _current_net_worth(user):
    # Personal-only and household-independent, same reasoning as
    # dashboard.services.net_worth_by_month: Accounts are never shared.
    totals = Transaction.objects.filter(user=user).aggregate(
        income=Sum("amount", filter=Q(type=Transaction.Type.INCOME)),
        expense=Sum("amount", filter=Q(type=Transaction.Type.EXPENSE)),
    )
    return (totals["income"] or Decimal("0")) - (totals["expense"] or Decimal("0"))


def project(
    user,
    household,
    trailing_months=DEFAULT_TRAILING_MONTHS,
    projection_months=DEFAULT_PROJECTION_MONTHS,
):
    months_with_data = _months_with_history(user, household, trailing_months)
    if len(months_with_data) < MIN_MONTHS_OF_HISTORY:
        return {
            "scope": {"household": household.id if household else None},
            "trailing_months": trailing_months,
            "insufficient_data": True,
            "message": "Not enough transaction history yet to project — check back after a couple of months.",
        }

    avg_income, avg_expense = trailing_average(user, household, trailing_months)
    avg_savings = avg_income - avg_expense
    recurring_by_month = _recurring_contribution_by_month(user, household, projection_months)

    current_month = date.today().replace(day=1)
    current_net_worth = _current_net_worth(user)
    net_worth = current_net_worth
    monthly_projection = []
    for i in range(projection_months):
        month = add_months(current_month, i)
        net_worth += avg_savings + recurring_by_month[month]
        monthly_projection.append({"month": month.isoformat(), "projected_net_worth": net_worth})

    return {
        "scope": {"household": household.id if household else None},
        "trailing_months": trailing_months,
        "insufficient_data": False,
        "avg_monthly_income": avg_income,
        "avg_monthly_expenses": avg_expense,
        "avg_monthly_savings": avg_savings,
        "current_net_worth": current_net_worth,
        "projection_months": projection_months,
        "projected_net_worth": monthly_projection[-1]["projected_net_worth"] if monthly_projection else None,
        "monthly_projection": monthly_projection,
        "message": (
            f"Projection based on your last {trailing_months} months — not a guarantee."
        ),
    }
