import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "generate-recurring-transactions-daily": {
        "task": "recurring_transactions.tasks.generate_recurring_transactions",
        "schedule": crontab(hour=1, minute=0),
    },
    "sweep-notifications-hourly": {
        "task": "notifications.tasks.sweep_notifications",
        "schedule": crontab(minute=0),
    },
}
