from decimal import Decimal

from rest_framework import serializers

from common.money import quantize

from . import services
from .models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    spent = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    utilization_pct = serializers.SerializerMethodField()
    daily_recommended_spend = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id",
            "household",
            "category",
            "month",
            "amount",
            "spent",
            "remaining",
            "utilization_pct",
            "daily_recommended_spend",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def _spent(self, budget):
        # Memoized per serializer instance: spent/remaining/utilization/
        # daily_recommended_spend would otherwise each independently
        # re-aggregate the same transaction query for the same row.
        cache = getattr(self, "_spent_cache", None)
        if cache is None:
            cache = self._spent_cache = {}
        if budget.id not in cache:
            cache[budget.id] = services.compute_spent(budget)
        return cache[budget.id]

    def get_spent(self, budget):
        return self._spent(budget)

    def get_remaining(self, budget):
        return budget.amount - self._spent(budget)

    def get_utilization_pct(self, budget):
        if budget.amount == 0:
            return None
        return quantize(self._spent(budget) / budget.amount * 100)

    def get_daily_recommended_spend(self, budget):
        return services.daily_recommended_spend(budget, spent=self._spent(budget))

    def validate_month(self, value):
        return value.replace(day=1)

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
