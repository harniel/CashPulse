from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimeStampedUUIDModel


class Transaction(TimeStampedUUIDModel):
    """
    Income/expense/transfer against one of the user's own accounts.
    `household` is the personal/shared switch (Section 7): null = visible
    only to `user`, set = visible to every member of that household.
    Accounts stay user-owned even when a transaction is shared — a
    transfer always moves money between accounts the *same* user owns.

    FKs use PROTECT rather than CASCADE/SET_NULL: a hard delete of an
    Account/Category/Household should never silently take transaction
    history down with it (Section 8) or leave an income/expense row with
    no category, which would violate clean() without going through it.
    """

    class Type(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"
        TRANSFER = "transfer", "Transfer"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )
    account = models.ForeignKey(
        "accounts.Account", on_delete=models.PROTECT, related_name="transactions"
    )
    to_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=10, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="PHP")
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["account", "date"]),
            models.Index(fields=["household", "date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="transaction_amount_positive"
            ),
            models.CheckConstraint(
                condition=~models.Q(type="transfer") | models.Q(category__isnull=True),
                name="transfer_has_no_category",
            ),
        ]

    def __str__(self):
        return f"{self.get_type_display()} {self.amount} {self.currency} ({self.date})"

    def clean(self):
        super().clean()
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
