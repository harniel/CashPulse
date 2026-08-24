from decimal import Decimal

from rest_framework import serializers

from . import services
from .models import SavingsContribution, SavingsGoal


class SavingsGoalSerializer(serializers.ModelSerializer):
    total_contributed = serializers.SerializerMethodField()
    progress_pct = serializers.SerializerMethodField()
    required_monthly_contribution = serializers.SerializerMethodField()
    is_behind_pace = serializers.SerializerMethodField()

    class Meta:
        model = SavingsGoal
        fields = [
            "id",
            "household",
            "name",
            "target_amount",
            "target_date",
            "total_contributed",
            "progress_pct",
            "required_monthly_contribution",
            "is_behind_pace",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_total_contributed(self, goal):
        return services.total_contributed(goal)

    def get_progress_pct(self, goal):
        return services.progress_pct(goal)

    def get_required_monthly_contribution(self, goal):
        return services.required_monthly_contribution(goal)

    def get_is_behind_pace(self, goal):
        return services.is_behind_pace(goal)

    def validate_target_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Target amount must be greater than zero.")
        return value


class SavingsContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsContribution
        fields = ["id", "date", "amount", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
