"""
Loan amortization and payoff-simulation math (Section 26 portfolio
differentiator #5). Decimal throughout, never float, per Section 14/29 —
Decimal supports integer exponentiation natively, so the standard
amortization formula needs no float detour.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from audit import services as audit
from common.dates import add_months
from common.money import quantize

from .models import Loan, LoanPayment

# Safety net against a runaway simulation loop, not a real product limit —
# 100 years of monthly payments is already far past any realistic loan term.
PAYOFF_SIMULATION_MONTH_CAP = 1200


def create_loan(user, **data):
    loan = Loan(user=user, **data)
    loan.save()
    return loan


def update_loan(loan, **data):
    for field, value in data.items():
        setattr(loan, field, value)
    loan.save()
    return loan


def monthly_payment(loan):
    """Standard fixed-rate amortization formula: M = P*r*(1+r)^n / ((1+r)^n - 1)."""
    r = loan.monthly_rate
    n = loan.term_months
    principal = loan.principal
    if r == 0:
        return quantize(principal / n)
    factor = (Decimal("1") + r) ** n
    return quantize(principal * r * factor / (factor - Decimal("1")))


def remaining_balance(loan):
    # Driven entirely by logged LoanPayment rows (both regular and extra) —
    # same "aggregate, don't store" pattern as Account.balance and
    # Budget.spent. This assumes every payment made gets logged, not just
    # the extra ones; the ERD's `is_extra` flag on every row is what
    # implies that's the intended usage.
    paid_principal = (
        loan.payments.aggregate(total=Sum("principal_portion"))["total"] or Decimal("0")
    )
    balance = loan.principal - paid_principal
    return balance if balance > 0 else Decimal("0")


def payoff_date(loan):
    """The original, theoretical payoff date if every payment is exactly
    on schedule — start_date + term_months, independent of what's
    actually been paid. Contrast with projected_payoff_date()."""
    return add_months(loan.start_date, loan.term_months)


def amortization_schedule(loan):
    """
    The theoretical schedule from day one — fixed monthly payment, no
    extra payments — not what's actually happened (see remaining_balance
    for that). Rounding drift is absorbed into the final row so the
    balance lands on exactly 0, the way a real lender's schedule does.
    """
    payment = monthly_payment(loan)
    r = loan.monthly_rate
    balance = loan.principal
    rows = []
    row_date = loan.start_date
    for month in range(1, loan.term_months + 1):
        interest_portion = quantize(balance * r)
        principal_portion = payment - interest_portion
        is_final_row = month == loan.term_months or principal_portion >= balance
        if is_final_row:
            principal_portion = balance
            payment_amount = principal_portion + interest_portion
            balance = Decimal("0")
        else:
            payment_amount = payment
            balance -= principal_portion
        rows.append(
            {
                "month": month,
                "date": row_date,
                "payment": payment_amount,
                "principal_portion": principal_portion,
                "interest_portion": interest_portion,
                "remaining_balance": balance,
            }
        )
        if is_final_row:
            break
        row_date = add_months(row_date, 1)
    return rows


def projected_payoff_date(loan, as_of=None):
    """
    "Log an extra payment and see the new payoff date" (Section 6):
    simulates forward from the loan's *actual* remaining_balance (which
    already reflects any extra payments logged), applying the same fixed
    monthly payment starting from `as_of` (default today) — not from the
    original schedule, so an extra payment visibly moves this date
    earlier than payoff_date(). Returns None if the payment can't even
    cover the interest due (balance would never shrink).
    """
    if as_of is None:
        as_of = date.today()
    balance = remaining_balance(loan)
    if balance <= 0:
        return as_of

    payment = monthly_payment(loan)
    r = loan.monthly_rate
    months = 0
    while balance > 0 and months < PAYOFF_SIMULATION_MONTH_CAP:
        interest_portion = quantize(balance * r)
        principal_portion = payment - interest_portion
        if principal_portion <= 0:
            return None
        balance -= min(principal_portion, balance)
        months += 1

    if balance > 0:
        return None
    return add_months(as_of, months)


def log_payment(loan, date_, amount, is_extra):
    if date_ < loan.start_date:
        raise ValidationError({"date": "Can't be before the loan's start date."})
    if amount <= 0:
        raise ValidationError({"amount": "Amount must be greater than zero."})

    balance_before = remaining_balance(loan)
    if balance_before <= 0:
        raise ValidationError("This loan is already paid off.")

    if is_extra:
        interest_portion = Decimal("0.00")
        principal_portion = amount
    else:
        interest_portion = quantize(balance_before * loan.monthly_rate)
        principal_portion = amount - interest_portion
        if principal_portion <= 0:
            raise ValidationError(
                {"amount": "Amount doesn't cover the interest due on this payment."}
            )

    if principal_portion > balance_before:
        raise ValidationError({"amount": "Payment exceeds the remaining balance."})

    payment = LoanPayment.objects.create(
        loan=loan,
        date=date_,
        amount=amount,
        principal_portion=principal_portion,
        interest_portion=interest_portion,
        is_extra=is_extra,
    )
    # Loans aren't household-shareable (no "someone else" scenario is
    # possible — OwnedModelViewSet only ever lets the owner reach it), so
    # the actor is always the loan's own user.
    audit.log(
        user=loan.user,
        household=None,
        action="create",
        entity_type="LoanPayment",
        entity_id=payment.id,
        metadata=audit.full_snapshot(payment),
    )
    return payment
