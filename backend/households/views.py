from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Household, HouseholdMembership, Invitation
from .permissions import HouseholdRolePermission
from .serializers import HouseholdMembershipSerializer, HouseholdSerializer, InvitationSerializer


class HouseholdViewSet(viewsets.ModelViewSet):
    """
    Scoped to households the requesting user is a member of — mirrors
    OwnedModelViewSet's "your data or 404" philosophy (Section 9), just
    with membership instead of ownership as the scoping relation.
    """

    serializer_class = HouseholdSerializer

    def get_queryset(self):
        return Household.objects.filter(memberships__user=self.request.user).distinct()

    def get_permissions(self):
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), HouseholdRolePermission(HouseholdMembership.Role.OWNER)()]
        if self.action in ("update", "partial_update", "invitations", "remove_member"):
            return [permissions.IsAuthenticated(), HouseholdRolePermission(HouseholdMembership.Role.ADMIN)()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        household = services.create_household(
            user=self.request.user, name=serializer.validated_data["name"]
        )
        serializer.instance = household

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, pk=None):
        household = self.get_object()
        memberships = household.memberships.select_related("user")
        return Response(HouseholdMembershipSerializer(memberships, many=True).data)

    @action(detail=True, methods=["delete"], url_path=r"members/(?P<user_id>[^/.]+)")
    def remove_member(self, request, pk=None, user_id=None):
        household = self.get_object()
        target_membership = get_object_or_404(
            HouseholdMembership, household=household, user_id=user_id
        )
        services.remove_member(
            household=household, actor=request.user, target_user=target_membership.user
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], url_path="invitations")
    def invitations(self, request, pk=None):
        household = self.get_object()
        if request.method == "GET":
            qs = household.invitations.select_related("invited_by")
            return Response(InvitationSerializer(qs, many=True).data)

        invitation = services.invite_member(
            household=household, invited_by=request.user, email=request.data.get("email", "")
        )
        return Response(InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="leave")
    def leave(self, request, pk=None):
        household = self.get_object()
        services.leave_household(household=household, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitationAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        invitation = get_object_or_404(Invitation, token=token)
        membership = services.accept_invitation(invitation=invitation, user=request.user)
        return Response(HouseholdMembershipSerializer(membership).data)


class InvitationDeclineView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        invitation = get_object_or_404(Invitation, token=token)
        services.decline_invitation(invitation=invitation, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
