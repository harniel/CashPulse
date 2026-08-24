from django.contrib import admin

from .models import SavingsContribution, SavingsGoal


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ["name", "target_amount", "target_date", "user", "household"]
    search_fields = ["name", "user__email"]


@admin.register(SavingsContribution)
class SavingsContributionAdmin(admin.ModelAdmin):
    list_display = ["goal", "date", "amount"]
    search_fields = ["goal__name"]
