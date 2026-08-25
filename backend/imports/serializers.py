from rest_framework import serializers

from .models import BudgetImportBatch, BudgetImportRow, ImportBatch, ImportRow


class ImportRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRow
        fields = ["id", "raw_data", "status", "error", "is_duplicate", "transaction", "created_at"]
        read_only_fields = fields


class ImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportBatch
        fields = [
            "id",
            "account",
            "filename",
            "status",
            "row_count",
            "date_column",
            "description_column",
            "amount_column",
            "created_at",
        ]
        read_only_fields = fields


class BudgetImportRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetImportRow
        fields = ["id", "row_number", "raw_data", "status", "action", "error", "budget", "created_at"]
        read_only_fields = fields


class BudgetImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetImportBatch
        fields = ["id", "filename", "status", "row_count", "created_at"]
        read_only_fields = fields
