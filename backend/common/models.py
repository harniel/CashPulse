import uuid

from django.db import models


class TimeStampedUUIDModel(models.Model):
    """
    Shared base for every finance-domain model: UUID primary key (not
    sequential — see users/models.py for the same reasoning) plus
    created_at/updated_at. Abstract, so it adds no extra table.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
