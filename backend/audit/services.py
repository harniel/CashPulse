"""
Audit logging helpers, called explicitly from other apps' services.py
(never signals — see the model docstring). `full_snapshot` and
`field_diff` are generic across any model, driven by `_meta.fields`, so
each app's services.py doesn't need to hand-list which columns matter.
"""

import datetime
from decimal import Decimal
from uuid import UUID

from .models import AuditLogEntry

_EXCLUDED_SNAPSHOT_FIELDS = {"created_at", "updated_at"}


def log(user, household, action, entity_type, entity_id, metadata=None):
    AuditLogEntry.objects.create(
        user=user,
        household=household,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
    )


def serialize_value(value):
    if value is None:
        return None
    if hasattr(value, "pk"):
        return str(value.pk)
    if isinstance(value, (Decimal, datetime.date, datetime.datetime, UUID)):
        return str(value)
    return value


def full_snapshot(instance):
    """Every concrete field on the instance except timestamps, as a
    JSON-safe dict — the "full row for deletes" Section 19 calls for."""
    return {
        field.name: serialize_value(getattr(instance, field.name))
        for field in instance._meta.fields
        if field.name not in _EXCLUDED_SNAPSHOT_FIELDS
    }


def field_diff(instance, changes):
    """{field: {"old": ..., "new": ...}} for whichever `changes` actually
    differ from the instance's current values — the update-diff shape
    Section 19 calls for. Call this *before* applying `changes` to
    `instance`."""
    diff = {}
    for field, new_value in changes.items():
        old_value = getattr(instance, field)
        if old_value != new_value:
            diff[field] = {
                "old": serialize_value(old_value),
                "new": serialize_value(new_value),
            }
    return diff
