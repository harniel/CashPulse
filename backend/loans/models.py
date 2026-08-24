from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStampedUUIDModel


class Loan(TimeStampedUUIDModel):
    """
    User-owned only — the blueprint's ERD (Section 8) doesn't give this
    table a `household` column the way Transaction/Budget/
    RecurringTransaction have, and the user stories (Section 6) don't
    mention sharing a loan, so unlike those three this isn't built on
    HouseholdScopedModelViewSet.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loans")
    lender = models.CharField(max_length=100, blank=True)
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=6, decimal_places=3)  # annual %, e.g. 5.500
    term_months = models.PositiveIntegerField()
    start_date = models.DateField()

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(condition=models.Q(principal__gt=0), name="loan_principal_positive"),
            models.CheckConstraint(
                condition=models.Q(interest_rate__gte=0), name="loan_interest_rate_non_negative"
            ),
            models.CheckConstraint(
                condition=models.Q(term_months__gt=0), name="loan_term_months_positive"
            ),
        ]

    def __str__(self):
        return f"{self.lender or 'Loan'} {self.principal} @ {self.interest_rate}%"

    @property
    def monthly_rate(self):
        return (self.interest_rate / Decimal("100")) / Decimal("12")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class LoanPayment(TimeStampedUUIDModel):
    """
    principal_portion/interest_portion are server-computed at logging
    time (services.log_payment), never client-supplied — same reasoning
    as Transaction's amount-sign convention: a value derived from the
    loan's state at that moment shouldn't be something the client asserts.
    CASCADE on `loan` (unlike Transaction's PROTECT-on-Account): a payment
    has no independent meaning outside its loan, so deleting the loan
    deleting its payment history is the right default, not silent data loss.
    """

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="payments")
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    principal_portion = models.DecimalField(max_digits=12, decimal_places=2)
    interest_portion = models.DecimalField(max_digits=12, decimal_places=2)
    is_extra = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date"]
        indexes = [models.Index(fields=["loan", "date"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="loan_payment_amount_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(amount=models.F("principal_portion") + models.F("interest_portion")),
                name="loan_payment_amount_matches_split",
            ),
        ]

    def __str__(self):
        return f"{self.loan} payment {self.amount} on {self.date}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
