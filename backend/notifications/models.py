from django.conf import settings
from django.db import models

from common.models import TimeStampedUUIDModel


class Notification(TimeStampedUUIDModel):
    """
    In-app only for V1 (Section 18) — email delivery is a documented
    extension point (the sweep task would be the natural place to also
    enqueue an email), not built. `payload` carries the structured data
    the frontend needs (amounts, entity id) rather than a pre-rendered
    string, so copy can change without a migration; `entity_id` lives
    inside `payload` (not a dedicated column) matching the ERD's literal
    column list (Section 8) — deduplication queries it via a JSON key
    lookup (`payload__entity_id=...`) instead.

    CASCADE on `household` (unlike Transaction/Budget/RecurringTransaction/
    SavingsGoal's PROTECT): a notification is a transient alert, not
    financial history — nothing is lost if a deleted household's
    notifications go with it.
    """

    class Type(models.TextChoices):
        BUDGET_EXCEEDED = "budget_exceeded", "Budget exceeded"
        BUDGET_APPROACHING = "budget_approaching", "Budget approaching"
        RECURRING_DUE_SOON = "recurring_due_soon", "Recurring due soon"
        LOAN_PAYMENT_DUE = "loan_payment_due", "Loan payment due"
        GOAL_BEHIND_PACE = "goal_behind_pace", "Goal behind pace"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at"])]

    def __str__(self):
        return f"{self.get_type_display()} for {self.user} ({'read' if self.read_at else 'unread'})"
