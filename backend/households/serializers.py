from rest_framework import serializers

from users.serializers import UserSerializer

from .models import Household, HouseholdMembership, Invitation


class HouseholdSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Household
        fields = ["id", "name", "created_by", "my_role", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "my_role", "created_at", "updated_at"]

    def get_my_role(self, household):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return None
        membership = household.memberships.filter(user=request.user).first()
        return membership.role if membership else None


class HouseholdMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = HouseholdMembership
        fields = ["id", "user", "role", "created_at"]
        read_only_fields = fields


class InvitationSerializer(serializers.ModelSerializer):
    invited_by = UserSerializer(read_only=True)

    class Meta:
        model = Invitation
        fields = ["id", "email", "token", "invited_by", "status", "expires_at", "created_at"]
        read_only_fields = ["id", "token", "invited_by", "status", "created_at"]
