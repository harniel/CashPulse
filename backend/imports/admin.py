from django.contrib import admin

from .models import ImportBatch, ImportRow


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ["filename", "account", "status", "row_count", "user"]
    list_filter = ["status"]
    search_fields = ["filename", "user__email"]


@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = ["batch", "status", "is_duplicate", "error"]
    list_filter = ["status", "is_duplicate"]
