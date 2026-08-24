from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "account_type", "currency", "is_active"]
    list_filter = ["account_type", "is_active", "currency"]
    search_fields = ["name", "user__email"]
