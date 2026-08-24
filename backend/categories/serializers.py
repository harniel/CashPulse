from rest_framework import serializers

from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "kind", "parent", "is_system", "created_at"]
        read_only_fields = ["id", "is_system", "created_at"]

    def validate_parent(self, parent):
        if parent is None:
            return parent
        if parent.parent_id is not None:
            raise serializers.ValidationError(
                "Categories can only be one level deep."
            )
        request = self.context.get("request")
        # A user may nest under a system category or their own category,
        # but not under someone else's custom category.
        if not parent.is_system and request and parent.user_id != request.user.id:
            raise serializers.ValidationError("You don't have access to that parent category.")
        return parent

    def validate(self, attrs):
        parent = attrs.get("parent") or getattr(self.instance, "parent", None)
        kind = attrs.get("kind") or getattr(self.instance, "kind", None)
        if parent and kind and parent.kind != kind:
            raise serializers.ValidationError(
                {"kind": "A category's kind must match its parent's kind."}
            )
        return attrs
