"""
One aggregation module backing GET /api/dashboard/summary/. Section 25:
"Dashboard summary is one endpoint issuing a small fixed set of aggregate
queries, not N widgets each firing their own request" — every figure here
is computed from Transaction/Budget, never stored, same as Account.balance
and Budget's own spent/remaining fields.
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

from budgets.models import Budget
from budgets.services import compute_spent
from common.money import quantize

# Re-exported so `dashboard.services.resolve_household` keeps working —
# now shared with forecasting/services.py, which needs the identical
# "optional ?household=<id> -> Household or a clean error" resolution.
from households.services import resolve_household  # noqa: F401
from transactions.models import Transaction

MONTHS_OF_HISTORY = 6
BUDGET_APPROACHING_THRESHOLD = Decimal("80")


def _month_bounds(month):
    last_day = calendar.monthrange(month.year, month.month)[1]
    return month, date(month.year, month.month, last_day)


def _shift_months(month, offset):
    total = month.month - 1 - offset
    year = month.year + total // 12
    return date(year, total % 12 + 1, 1)


def _scoped_transactions(user, household):
    if household is not None:
        return Transaction.objects.filter(household=household)
    return Transaction.objects.filter(user=user, household__isnull=True)


def _income_expense_totals(queryset):
    totals = queryset.aggregate(
        income=Sum("amount", filter=Q(type=Transaction.Type.INCOME)),
        expense=Sum("amount", filter=Q(type=Transaction.Type.EXPENSE)),
    )
    return totals["income"] or Decimal("0"), totals["expense"] or Decimal("0")


def cash_flow_by_month(user, household, months=MONTHS_OF_HISTORY):
    current_month = date.today().replace(day=1)
    series = []
    for i in range(months - 1, -1, -1):
        month = _shift_months(current_month, i)
        start, end = _month_bounds(month)
        income, expense = _income_expense_totals(
            _scoped_transactions(user, household).filter(date__gte=start, date__lte=end)
        )
        series.append(
            {"month": month.isoformat(), "income": income, "expense": expense, "net": income - expense}
        )
    return series


def net_worth_by_month(user, months=MONTHS_OF_HISTORY):
    # Personal-only, regardless of the dashboard's household scope:
    # Accounts are never shared (Section 7), so net worth is always the
    # requesting user's own. Transfers net to zero across a user's own
    # accounts, so only income/expense affect the running total — the
    # same simplification Section 15's forecasting design relies on.
    current_month = date.today().replace(day=1)
    series = []
    for i in range(months - 1, -1, -1):
        month = _shift_months(current_month, i)
        _, end = _month_bounds(month)
        income, expense = _income_expense_totals(Transaction.objects.filter(user=user, date__lte=end))
        series.append({"month": month.isoformat(), "net_worth": income - expense})
    return series


def spending_by_category(user, household, month):
    start, end = _month_bounds(month)
    qs = _scoped_transactions(user, household).filter(
        type=Transaction.Type.EXPENSE, date__gte=start, date__lte=end
    )
    rows = (
        qs.values("category__id", "category__name")
        .annotate(amount=Sum("amount"))
        .order_by("-amount")
    )
    return [
        {"category_id": row["category__id"], "category": row["category__name"], "amount": row["amount"]}
        for row in rows
    ]


def budget_utilization(user, household, month):
    qs = Budget.objects.filter(month=month).select_related("category")
    qs = qs.filter(household=household) if household is not None else qs.filter(
        user=user, household__isnull=True
    )

    rows = []
    for budget in qs:
        spent = compute_spent(budget)
        utilization_pct = quantize(spent / budget.amount * 100) if budget.amount else None
        rows.append(
            {
                "budget_id": budget.id,
                "category": budget.category.name,
                "amount": budget.amount,
                "spent": spent,
                "utilization_pct": utilization_pct,
            }
        )
    return rows


def compute_insights(user, household, month, budget_rows, month_income, month_expense):
    insights = []
    for row in budget_rows:
        if row["utilization_pct"] is None:
            continue
        if row["utilization_pct"] >= 100:
            insights.append(
                {
                    "type": "budget_exceeded",
                    "category": row["category"],
                    "message": (
                        f"You've gone over your {row['category']} budget this month "
                        f"({row['spent']} of {row['amount']})."
                    ),
                }
            )
        elif row["utilization_pct"] >= BUDGET_APPROACHING_THRESHOLD:
            insights.append(
                {
                    "type": "budget_approaching",
                    "category": row["category"],
                    "message": (
                        f"You're at {row['utilization_pct']}% of your {row['category']} "
                        f"budget this month."
                    ),
                }
            )

    if month_income > 0 and month_expense > month_income:
        insights.append(
            {
                "type": "negative_cash_flow",
                "message": (
                    f"You've spent more than you've earned this month "
                    f"({month_expense} vs {month_income})."
                ),
            }
        )

    return insights


def summary(user, household):
    current_month = date.today().replace(day=1)
    start, end = _month_bounds(current_month)

    income, expense = _income_expense_totals(
        _scoped_transactions(user, household).filter(date__gte=start, date__lte=end)
    )
    savings_rate_pct = quantize((income - expense) / income * 100) if income > 0 else None

    worth_series = net_worth_by_month(user)
    budget_rows = budget_utilization(user, household, current_month)

    return {
        "scope": {"household": household.id if household else None},
        "month": current_month,
        "net_cash_flow": income - expense,
        "savings_rate_pct": savings_rate_pct,
        "net_worth": worth_series[-1]["net_worth"],
        "charts": {
            "cash_flow_by_month": cash_flow_by_month(user, household),
            "spending_by_category": spending_by_category(user, household, current_month),
            "net_worth_by_month": worth_series,
            "budget_utilization": budget_rows,
        },
        "insights": compute_insights(user, household, current_month, budget_rows, income, expense),
    }
