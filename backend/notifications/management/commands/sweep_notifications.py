from django.core.management.base import BaseCommand

from notifications import services


class Command(BaseCommand):
    help = "Evaluate notification rules (budgets, recurring, loans, goals) and create any that are due."

    def handle(self, *args, **options):
        counts = services.sweep()
        total = sum(counts.values())
        self.stdout.write(self.style.SUCCESS(f"Created {total} notification(s): {counts}"))
