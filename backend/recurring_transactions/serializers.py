from decimal import Decimal

from rest_framework import serializers

from .models import RecurringTransaction


class RecurringTransactionSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)

    class Meta:
        model = RecurringTransaction
        fields = [
            "id",
            "household",
            "account",
            "to_account",
            "category",
            "type",
            "type_display",
            "amount",
            "currency",
            "description",
            "notes",
            "frequency",
            "frequency_display",
            "next_run_date",
            "end_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "currency", "created_at", "updated_at"]

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate(self, attrs):
        # Mirrors RecurringTransaction.clean() for a clean 400 — same
        # pattern as TransactionSerializer.validate().
        def resolve(field):
            if field in attrs:
                return attrs[field]
            return getattr(self.instance, field, None)

        type_ = resolve("type")
        category = resolve("category")
        to_account = resolve("to_account")
        account = resolve("account")
        next_run_date = resolve("next_run_date")
        end_date = resolve("end_date")

        if end_date is not None and next_run_date is not None and end_date < next_run_date:
            raise serializers.ValidationError(
                {"end_date": "Can't be before the next run date."}
            )

        if type_ == RecurringTransaction.Type.TRANSFER:
            if category is not None:
                raise serializers.ValidationError(
                    {"category": "Transfers can't have a category."}
                )
            if to_account is None:
                raise serializers.ValidationError(
                    {"to_account": "Transfers need a destination account."}
                )
            if account is not None and to_account == account:
                raise serializers.ValidationError(
                    {"to_account": "Must differ from the source account."}
                )
        else:
            if to_account is not None:
                raise serializers.ValidationError(
                    {"to_account": "Only transfers can have a destination account."}
                )
            if category is None:
                raise serializers.ValidationError(
                    {"category": "Income and expense transactions need a category."}
                )
            elif category.kind != type_:
                raise serializers.ValidationError(
                    {"category": "The category's kind must match the transaction type."}
                )
        return attrs
