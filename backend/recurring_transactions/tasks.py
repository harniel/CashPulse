from celery import shared_task

from . import services


@shared_task
def generate_recurring_transactions():
    """Wired into Celery beat (config/celery.py). Thin on purpose — the
    actual engine is services.generate_due_occurrences(), which is what's
    unit-tested and what the `generate_recurring_transactions` management
    command calls directly, without needing a broker running."""
    generated = services.generate_due_occurrences()
    return len(generated)
