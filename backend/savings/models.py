from django.conf import settings
from django.db import models

from common.models import TimeStampedUUIDModel


class SavingsGoal(TimeStampedUUIDModel):
    """
    Household-shareable like Transaction/Budget/RecurringTransaction (the
    ERD, Section 8, gives `savings_savingsgoal` a nullable `household_id`,
    unlike Loan) — built on HouseholdScopedModelViewSet for the same
    "yours, or your household's" visibility rule.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="savings_goals"
    )
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.PROTECT,
        related_name="savings_goals",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    target_date = models.DateField()

    class Meta:
        ordering = ["target_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(target_amount__gt=0), name="savings_goal_target_amount_positive"
            ),
        ]

    def __str__(self):
        return f"{self.name} (target {self.target_amount} by {self.target_date})"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SavingsContribution(TimeStampedUUIDModel):
    """CASCADE on `goal`: a contribution has no independent meaning
    outside its goal, same reasoning as LoanPayment vs. Loan."""

    goal = models.ForeignKey(SavingsGoal, on_delete=models.CASCADE, related_name="contributions")
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["-date"]
        indexes = [models.Index(fields=["goal", "date"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="savings_contribution_amount_positive"
            ),
        ]

    def __str__(self):
        return f"{self.goal} +{self.amount} on {self.date}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
