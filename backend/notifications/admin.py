from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["type", "user", "household", "read_at", "created_at"]
    list_filter = ["type"]
    search_fields = ["user__email"]
