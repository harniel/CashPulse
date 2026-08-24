from django.conf import settings
from django.db import models

from common.models import TimeStampedUUIDModel


class Budget(TimeStampedUUIDModel):
    """
    One spending limit for one category in one month. `month` is always
    normalized to the 1st (see save()) — it's a period key, not a real date.

    Personal (household=None) and shared budgets each need their own
    uniqueness rule rather than one UniqueConstraint across all four
    columns: `household` is nullable, and SQL/Django both treat NULL as
    never equal to NULL, so a single constraint including it would never
    fire for personal budgets — the same trap fixed for Category's
    top-level uniqueness. A shared budget is one row per
    (household, category, month) regardless of which member created it;
    `user` there just records who did, it isn't part of the identity.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets"
    )
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.PROTECT,
        related_name="budgets",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        "categories.Category", on_delete=models.PROTECT, related_name="budgets"
    )
    month = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["-month", "category__name"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="budget_amount_positive"),
            models.UniqueConstraint(
                fields=["user", "category", "month"],
                condition=models.Q(household__isnull=True),
                name="unique_personal_budget_per_user_category_month",
            ),
            models.UniqueConstraint(
                fields=["household", "category", "month"],
                condition=models.Q(household__isnull=False),
                name="unique_shared_budget_per_household_category_month",
            ),
        ]

    def __str__(self):
        return f"{self.category} {self.month:%Y-%m} ({self.amount})"

    def save(self, *args, **kwargs):
        self.month = self.month.replace(day=1)
        self.full_clean()
        super().save(*args, **kwargs)
