import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import TimeStampedUUIDModel


def generate_invitation_token():
    return secrets.token_urlsafe(32)


def default_invitation_expiry():
    return timezone.now() + timedelta(days=7)


class Household(TimeStampedUUIDModel):
    """
    The tenancy boundary for shared data (Section 3 of the blueprint).
    Accounts/Categories stay user-owned; it's Transaction (added in a
    later step) that gets a nullable household FK — this app only needs
    to own the household itself, membership, and invitations.
    """

    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_households"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class HouseholdMembership(TimeStampedUUIDModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="household_memberships"
    )
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        ordering = ["household", "user__email"]
        constraints = [
            # A user can only have one membership row per household — role
            # changes update this row, they don't add a second one.
            models.UniqueConstraint(
                fields=["user", "household"], name="unique_membership_per_user_per_household"
            )
        ]
        indexes = [models.Index(fields=["household"])]

    def __str__(self):
        return f"{self.user} @ {self.household} ({self.role})"


class Invitation(TimeStampedUUIDModel):
    """
    Email-addressed, token-bearing invite to join a household. Not tied
    to an existing User row (the invitee may not have an account yet) —
    acceptance is resolved by matching the authenticated user's email
    against `email` at accept time (see services.accept_invitation).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_invitations"
    )
    token = models.CharField(
        max_length=64, unique=True, default=generate_invitation_token, editable=False
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField(default=default_invitation_expiry)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Only one *pending* invite per (household, email) at a time —
            # re-inviting reuses/updates that row (see services.invite_member)
            # rather than piling up duplicates. Past invitations (accepted/
            # declined/expired/cancelled) are excluded so history isn't lost.
            models.UniqueConstraint(
                fields=["household", "email"],
                condition=models.Q(status="pending"),
                name="unique_pending_invitation_per_household_email",
            )
        ]

    def __str__(self):
        return f"{self.email} -> {self.household} ({self.status})"
