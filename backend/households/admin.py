from django.contrib import admin

from .models import Household, HouseholdMembership, Invitation


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at"]
    search_fields = ["name", "created_by__email"]


@admin.register(HouseholdMembership)
class HouseholdMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "household", "role"]
    list_filter = ["role"]
    search_fields = ["user__email", "household__name"]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "household", "status", "invited_by", "expires_at"]
    list_filter = ["status"]
    search_fields = ["email", "household__name"]
