from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["date", "type", "amount", "currency", "account", "user", "household"]
    list_filter = ["type", "currency"]
    search_fields = ["description", "user__email", "account__name"]
