from django.contrib import admin

from .models import GeneratedOccurrence, RecurringTransaction


@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ["description", "type", "amount", "frequency", "next_run_date", "user", "household"]
    list_filter = ["type", "frequency"]
    search_fields = ["description", "user__email"]


@admin.register(GeneratedOccurrence)
class GeneratedOccurrenceAdmin(admin.ModelAdmin):
    list_display = ["recurring", "due_date", "transaction"]
    search_fields = ["recurring__description"]
