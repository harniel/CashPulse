from decimal import Decimal

from rest_framework import serializers

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Transaction
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
            "date",
            "description",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "currency", "created_at", "updated_at"]

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate(self, attrs):
        # Mirrors Transaction.clean() so a shape mistake (wrong category/
        # to_account for the given type) gets a clean 400 here rather than
        # surfacing as a raw django ValidationError out of model.save().
        def resolve(field):
            if field in attrs:
                return attrs[field]
            return getattr(self.instance, field, None)

        type_ = resolve("type")
        category = resolve("category")
        to_account = resolve("to_account")
        account = resolve("account")

        if type_ == Transaction.Type.TRANSFER:
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
