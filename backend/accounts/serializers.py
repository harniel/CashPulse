from rest_framework import serializers

from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(
        source="get_account_type_display", read_only=True
    )
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "name",
            "account_type",
            "account_type_display",
            "currency",
            "institution",
            "is_active",
            "balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, name):
        # The UniqueConstraint on (user, name) lives in the DB, but
        # 'user' isn't a serializer field (it's set server-side in
        # perform_create), so DRF can't auto-derive a UniqueTogetherValidator
        # for it. Without this check the constraint still fires — just as
        # an unhandled IntegrityError (500) instead of a clean 400.
        request = self.context.get("request")
        if request is None:
            return name
        queryset = Account.objects.filter(user=request.user, name=name)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("You already have an account with this name.")
        return name
