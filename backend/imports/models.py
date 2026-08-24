from django.conf import settings
from django.db import models

from common.models import TimeStampedUUIDModel


class ImportBatch(TimeStampedUUIDModel):
    """
    One uploaded CSV, imported against a single Account (matching the ERD,
    Section 8 — there's no per-row account column; "account" in the user
    story's "map CSV headers to date/description/amount/account" means
    picking the one target Account for the whole batch, not a CSV
    column). `date_column`/`description_column`/`amount_column` are the
    mapping chosen at upload time, stored so `confirm()` can re-derive
    structured values from each row's `raw_data` without the client
    needing to resubmit the mapping.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="import_batches"
    )
    account = models.ForeignKey(
        "accounts.Account", on_delete=models.PROTECT, related_name="import_batches"
    )
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    row_count = models.PositiveIntegerField()
    date_column = models.CharField(max_length=100)
    description_column = models.CharField(max_length=100)
    amount_column = models.CharField(max_length=100)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} ({self.row_count} rows, {self.status})"


class ImportRow(TimeStampedUUIDModel):
    """
    One CSV row's outcome, kept even after failure/skip — Section 16's
    "easy 'why did row 47 fail' debugging" goal. `is_duplicate` is
    independent of `status`: it's set once, at upload time, and survives
    regardless of what the user later decides to do with the row (a
    flag, not an auto-skip — Section 16).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IMPORTED = "imported", "Imported"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="rows")
    raw_data = models.JSONField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    error = models.CharField(max_length=255, blank=True)
    is_duplicate = models.BooleanField(default=False)
    # PROTECT, not CASCADE: the transaction this row created must stay
    # linked to its audit trail even if something tried to delete it —
    # same reasoning as GeneratedOccurrence.transaction.
    transaction = models.OneToOneField(
        "transactions.Transaction",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="import_row",
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["batch"])]

    def __str__(self):
        return f"{self.batch} row ({self.status})"
