from rest_framework import permissions

from .models import HouseholdMembership

_ROLE_RANK = {
    HouseholdMembership.Role.MEMBER: 0,
    HouseholdMembership.Role.ADMIN: 1,
    HouseholdMembership.Role.OWNER: 2,
}


def HouseholdRolePermission(minimum_role):
    """
    Factory rather than a plain class: DRF instantiates each entry in
    `permission_classes` with no arguments, so parameterizing "how senior
    a role must be" (Section 13 of the blueprint) needs a closure that
    returns a fresh BasePermission subclass per call.

    This is the second, narrower gate on top of HouseholdViewSet's
    membership-scoped get_queryset (§9's "must be a member at all" layer) —
    has_object_permission only runs once get_object() has already
    confirmed the requesting user belongs to the household.
    """

    class _HouseholdRolePermission(permissions.BasePermission):
        def has_permission(self, request, view):
            return bool(request.user and request.user.is_authenticated)

        def has_object_permission(self, request, view, household):
            membership = HouseholdMembership.objects.filter(
                user=request.user, household=household
            ).first()
            if membership is None:
                return False
            return _ROLE_RANK[membership.role] >= _ROLE_RANK[minimum_role]

    return _HouseholdRolePermission
