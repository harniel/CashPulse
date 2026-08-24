from rest_framework import serializers

from .models import ImportBatch, ImportRow


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
