from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStampedUUIDModel


class Account(TimeStampedUUIDModel):
    """
    A place money lives: a wallet, bank account, card, etc.

    Deliberately has NO stored balance field. Per Section 14 of the
    blueprint, balance is always computed as
    SUM(transactions for this account, signed by type) — a stored
    balance can silently drift from reality if any write path forgets
    to update it, which is the worst possible bug class in a finance
    app. The cost is a small aggregate query per account instead of a
    column read; see the `balance` property below.
    """

    class AccountType(models.TextChoices):
        CASH = "cash", "Cash"
        BANK = "bank", "Bank account"
        E_WALLET = "e_wallet", "E-wallet"
        CREDIT_CARD = "credit_card", "Credit card"
        SAVINGS = "savings", "Savings account"
        LOAN = "loan", "Loan account"
        INVESTMENT = "investment", "Investment account"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accounts"
    )
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    currency = models.CharField(max_length=3, default="PHP")
    institution = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_active", "name"]
        constraints = [
            # Prevents "Cash", "Cash", "Cash" clutter per user — same
            # account name twice is almost certainly a mistake, not intent.
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_account_name_per_user"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

    @property
    def balance(self):
        # Imported lazily: transactions/models.py FKs to Account, so a
        # module-level import here would be circular.
        from django.db.models import Q, Sum

        from transactions.models import Transaction

        as_source = Transaction.objects.filter(account=self).aggregate(
            income=Sum("amount", filter=Q(type=Transaction.Type.INCOME)),
            expense=Sum("amount", filter=Q(type=Transaction.Type.EXPENSE)),
            transfer_out=Sum("amount", filter=Q(type=Transaction.Type.TRANSFER)),
        )
        transfer_in = Transaction.objects.filter(
            to_account=self, type=Transaction.Type.TRANSFER
        ).aggregate(total=Sum("amount"))["total"]

        income = as_source["income"] or Decimal("0")
        expense = as_source["expense"] or Decimal("0")
        transfer_out = as_source["transfer_out"] or Decimal("0")
        transfer_in = transfer_in or Decimal("0")

        return income - expense - transfer_out + transfer_in
