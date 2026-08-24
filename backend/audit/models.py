from django.conf import settings
from django.db import models

from common.models import TimeStampedUUIDModel


class AuditLogEntry(TimeStampedUUIDModel):
    """
    Written by explicit `audit.log(...)` calls inside each app's
    services.py (Section 9) — never Django signals, so "what happens when
    a transaction is deleted" stays visible in the same place as the
    business logic describing it, and is trivial to unit test without
    wiring up signal receivers.

    `household` uses SET_NULL, not CASCADE or PROTECT: the whole point of
    an audit entry is to survive the thing it describes (Section 8 — "a
    hard-deleted transaction still has to be auditable"), so it must not
    disappear just because the household itself is later deleted; but it
    also can't PROTECT that deletion, or a household could never actually
    be deleted once anything had ever happened in it.
    """

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="audit_log_entries"
    )
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.SET_NULL,
        related_name="audit_log_entries",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "audit log entries"
        indexes = [
            models.Index(fields=["household", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type}({self.entity_id}) by {self.user}"
