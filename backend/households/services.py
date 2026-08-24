"""
Business logic for households — validation-that-spans-models, role checks,
and (eventually) audit logging live here rather than in views/serializers,
per Section 9 of the blueprint.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction as db_transaction
from django.db.models import ProtectedError
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from audit import services as audit

from .models import Household, HouseholdMembership, Invitation

INVITATION_LIFETIME = timedelta(days=7)

_ROLE_RANK = {
    HouseholdMembership.Role.MEMBER: 0,
    HouseholdMembership.Role.ADMIN: 1,
    HouseholdMembership.Role.OWNER: 2,
}


def resolve_household(user, household_id):
    """None (personal scope) unless a household id is given and the user
    is actually a member of it — used by any read-only, scope-by-query-
    param endpoint (dashboard summary, forecast) that needs to turn an
    optional ?household=<id> into an actual Household or a clean error."""
    if not household_id:
        return None
    try:
        membership = (
            HouseholdMembership.objects.filter(user=user, household_id=household_id)
            .select_related("household")
            .first()
        )
    except (ValueError, DjangoValidationError):
        raise ValidationError({"household": "Not a valid UUID."})
    if membership is None:
        raise PermissionDenied("You're not a member of that household.")
    return membership.household


def create_household(user, name):
    with db_transaction.atomic():
        household = Household.objects.create(name=name, created_by=user)
        HouseholdMembership.objects.create(
            user=user, household=household, role=HouseholdMembership.Role.OWNER
        )
    return household


def _require_role(household, user, minimum_role):
    membership = HouseholdMembership.objects.filter(user=user, household=household).first()
    if membership is None or _ROLE_RANK[membership.role] < _ROLE_RANK[minimum_role]:
        raise PermissionDenied("You don't have permission to do that in this household.")
    return membership


def invite_member(household, invited_by, email):
    _require_role(household, invited_by, HouseholdMembership.Role.ADMIN)
    email = (email or "").strip().lower()
    if not email:
        raise ValidationError({"email": "This field is required."})
    if HouseholdMembership.objects.filter(
        household=household, user__email__iexact=email
    ).exists():
        raise ValidationError("That person is already a member of this household.")

    # Re-inviting while a pending invite exists updates it (fresh expiry,
    # same token) instead of hitting the unique-pending constraint.
    invitation, _created = Invitation.objects.update_or_create(
        household=household,
        email=email,
        status=Invitation.Status.PENDING,
        defaults={
            "invited_by": invited_by,
            "expires_at": timezone.now() + INVITATION_LIFETIME,
        },
    )
    return invitation


def remove_member(household, actor, target_user):
    _require_role(household, actor, HouseholdMembership.Role.ADMIN)
    membership = HouseholdMembership.objects.filter(household=household, user=target_user).first()
    if membership is None:
        raise NotFound("That user is not a member of this household.")
    if membership.role == HouseholdMembership.Role.OWNER:
        raise ValidationError(
            "The household owner can't be removed — transfer ownership first."
        )
    membership_id = membership.id
    membership.delete()
    audit.log(
        user=actor,
        household=household,
        action="delete",
        entity_type="HouseholdMembership",
        entity_id=membership_id,
        metadata={"removed_user": str(target_user.id)},
    )


def leave_household(household, user):
    membership = HouseholdMembership.objects.filter(household=household, user=user).first()
    if membership is None:
        raise NotFound()

    if membership.role == HouseholdMembership.Role.OWNER:
        other_members_exist = (
            HouseholdMembership.objects.filter(household=household).exclude(user=user).exists()
        )
        if other_members_exist:
            raise ValidationError(
                "You're the owner of this household — transfer ownership to another "
                "member before leaving."
            )
        # Sole remaining member and owner: leaving removes the household itself
        # rather than orphaning it with no owner.
        try:
            household.delete()
        except ProtectedError:
            raise ValidationError(
                "This household has shared transactions and can't be deleted — "
                "you can't leave it while you're its only member."
            )
        return

    membership_id = membership.id
    membership.delete()
    audit.log(
        user=user,
        household=household,
        action="delete",
        entity_type="HouseholdMembership",
        entity_id=membership_id,
        metadata={"removed_user": str(user.id), "self_removed": True},
    )


def accept_invitation(invitation, user):
    _validate_invitation_for_user(invitation, user)

    with db_transaction.atomic():
        membership, created = HouseholdMembership.objects.get_or_create(
            user=user,
            household=invitation.household,
            defaults={"role": HouseholdMembership.Role.MEMBER},
        )
        invitation.status = Invitation.Status.ACCEPTED
        invitation.save(update_fields=["status"])
    if created:
        audit.log(
            user=user,
            household=invitation.household,
            action="create",
            entity_type="HouseholdMembership",
            entity_id=membership.id,
            metadata=audit.full_snapshot(membership),
        )
    return membership


def decline_invitation(invitation, user):
    _validate_invitation_for_user(invitation, user)
    invitation.status = Invitation.Status.DECLINED
    invitation.save(update_fields=["status"])


def _validate_invitation_for_user(invitation, user):
    if invitation.status != Invitation.Status.PENDING:
        raise ValidationError("This invitation is no longer valid.")
    if invitation.expires_at < timezone.now():
        invitation.status = Invitation.Status.EXPIRED
        invitation.save(update_fields=["status"])
        raise ValidationError("This invitation has expired.")
    if invitation.email.lower() != user.email.lower():
        raise PermissionDenied("This invitation was sent to a different email address.")
