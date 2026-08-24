from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimeStampedUUIDModel


class RecurringTransaction(TimeStampedUUIDModel):
    """
    A template that generates real Transaction rows on a schedule
    (Section 17's daily Celery beat job, or `generate_due_occurrences()`
    run manually/via a management command). Fields mirror Transaction —
    same personal/shared split via `household`, same shape rules
    (transfer vs. category) — because each generated row IS a Transaction,
    just stamped out repeatedly instead of entered once.
    """

    class Type(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"
        TRANSFER = "transfer", "Transfer"

    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Every 2 weeks"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recurring_transactions"
    )
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.PROTECT,
        related_name="recurring_transactions",
        null=True,
        blank=True,
    )
    account = models.ForeignKey(
        "accounts.Account", on_delete=models.PROTECT, related_name="recurring_transactions"
    )
    to_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="recurring_incoming_transfers",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.PROTECT,
        related_name="recurring_transactions",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=10, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="PHP")
    description = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    frequency = models.CharField(max_length=10, choices=Frequency.choices)
    next_run_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["next_run_date"]
        indexes = [models.Index(fields=["next_run_date"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="recurring_amount_positive"
            ),
        ]

    def __str__(self):
        return f"{self.get_type_display()} {self.amount} {self.currency} every {self.frequency}"

    def clean(self):
        super().clean()
        # end_date < next_run_date is checked in the serializer, not here:
        # generate_due_occurrences() legitimately walks next_run_date past
        # end_date as the terminal "nothing left to generate" state, and
        # that save() must not be rejected — the check only makes sense as
        # a sanity check on user input, not as a lifelong model invariant.
        if self.type == self.Type.TRANSFER:
            if self.category_id is not None:
                raise ValidationError("Transfers can't have a category.")
            if self.to_account_id is None:
                raise ValidationError("Transfers need a destination account.")
            if self.to_account_id == self.account_id:
                raise ValidationError(
                    "A transfer's destination account must differ from its source account."
                )
        else:
            if self.to_account_id is not None:
                raise ValidationError("Only transfers can have a destination account.")
            if self.category_id is None:
                raise ValidationError("Income and expense transactions need a category.")
            elif self.category.kind != self.type:
                raise ValidationError("The category's kind must match the transaction type.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class GeneratedOccurrence(TimeStampedUUIDModel):
    """
    One row per (recurring, due_date) actually posted — the unique
    constraint below is what makes generation idempotent: a retried or
    duplicated task run for the same due_date hits an IntegrityError on
    the second attempt instead of double-posting (Section 17).
    """

    recurring = models.ForeignKey(
        RecurringTransaction, on_delete=models.CASCADE, related_name="occurrences"
    )
    due_date = models.DateField()
    # PROTECT, not CASCADE: deleting a RecurringTransaction template must
    # never delete the real Transaction rows it already generated — only
    # the bookkeeping link (this row, which does cascade from `recurring`).
    transaction = models.OneToOneField(
        "transactions.Transaction", on_delete=models.PROTECT, related_name="generated_occurrence"
    )

    class Meta:
        ordering = ["-due_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["recurring", "due_date"], name="unique_occurrence_per_recurring_due_date"
            )
        ]

    def __str__(self):
        return f"{self.recurring} @ {self.due_date}"
