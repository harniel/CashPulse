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
    app. The `balance` property below (added once the Transaction model
    exists in a later step) will do that computation; for now this app
    only owns the account itself.
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
