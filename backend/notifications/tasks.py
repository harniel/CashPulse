from celery import shared_task

from . import services


@shared_task
def sweep_notifications():
    """Wired into Celery beat (config/celery.py), same thin-wrapper
    pattern as recurring_transactions/tasks.py — the actual rules live in
    services.sweep(), unit-tested and runnable without a broker via the
    `sweep_notifications` management command."""
    return services.sweep()
