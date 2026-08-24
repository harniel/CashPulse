from decimal import Decimal

from rest_framework import serializers

from . import services
from .models import Loan, LoanPayment


class LoanSerializer(serializers.ModelSerializer):
    monthly_payment = serializers.SerializerMethodField()
    remaining_balance = serializers.SerializerMethodField()
    payoff_date = serializers.SerializerMethodField()
    projected_payoff_date = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            "id",
            "lender",
            "principal",
            "interest_rate",
            "term_months",
            "start_date",
            "monthly_payment",
            "remaining_balance",
            "payoff_date",
            "projected_payoff_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_monthly_payment(self, loan):
        return services.monthly_payment(loan)

    def get_remaining_balance(self, loan):
        return services.remaining_balance(loan)

    def get_payoff_date(self, loan):
        return services.payoff_date(loan)

    def get_projected_payoff_date(self, loan):
        return services.projected_payoff_date(loan)

    def validate_principal(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Principal must be greater than zero.")
        return value

    def validate_interest_rate(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError("Interest rate can't be negative.")
        return value

    def validate_term_months(self, value):
        if value <= 0:
            raise serializers.ValidationError("Term must be at least 1 month.")
        return value


class LoanPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanPayment
        fields = ["id", "date", "amount", "principal_portion", "interest_portion", "is_extra", "created_at"]
        read_only_fields = ["id", "principal_portion", "interest_portion", "created_at"]

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
