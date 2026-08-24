from django.core.management.base import BaseCommand

from recurring_transactions import services


class Command(BaseCommand):
    """
    Runs the same engine as the Celery beat job (Section 17), without
    needing Celery/Redis running — the "run now" alternative to a live
    scheduler that Section 30 calls for so a portfolio deploy doesn't
    need to keep Celery up 24/7 just to look complete.
    """

    help = "Post any Transaction rows owed by due RecurringTransactions."

    def handle(self, *args, **options):
        generated = services.generate_due_occurrences()
        self.stdout.write(self.style.SUCCESS(f"Generated {len(generated)} transaction(s)."))
