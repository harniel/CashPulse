from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from households.models import Household, HouseholdMembership, Invitation
from households.tests.factories import (
    HouseholdFactory,
    HouseholdMembershipFactory,
    InvitationFactory,
)
from users.tests.factories import UserFactory


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def add_member(household, user, role=HouseholdMembership.Role.MEMBER):
    return HouseholdMembershipFactory(household=household, user=user, role=role)


@pytest.mark.django_db
class TestHouseholdCRUD:
    def test_create_household_makes_creator_owner(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.post("/api/households/", {"name": "The Smiths"})
        assert response.status_code == 201
        household = Household.objects.get(id=response.data["id"])
        assert household.created_by_id == user.id
        membership = HouseholdMembership.objects.get(household=household, user=user)
        assert membership.role == HouseholdMembership.Role.OWNER
        assert response.data["my_role"] == "owner"

    def test_list_only_returns_households_im_a_member_of(self):
        user = UserFactory()
        mine = HouseholdFactory()
        add_member(mine, user)
        HouseholdFactory()  # not mine

        client = authed_client(user)
        response = client.get("/api/households/")
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == str(mine.id)

    def test_non_member_gets_404_on_retrieve(self):
        household = HouseholdFactory()
        client = authed_client(UserFactory())
        response = client.get(f"/api/households/{household.id}/")
        assert response.status_code == 404

    def test_owner_can_rename_household(self):
        user = UserFactory()
        household = HouseholdFactory()
        add_member(household, user, role=HouseholdMembership.Role.OWNER)
        client = authed_client(user)
        response = client.patch(f"/api/households/{household.id}/", {"name": "New Name"})
        assert response.status_code == 200
        household.refresh_from_db()
        assert household.name == "New Name"

    def test_regular_member_cannot_rename_household(self):
        user = UserFactory()
        household = HouseholdFactory()
        add_member(household, user, role=HouseholdMembership.Role.MEMBER)
        client = authed_client(user)
        response = client.patch(f"/api/households/{household.id}/", {"name": "Hijacked"})
        assert response.status_code == 403

    def test_only_owner_can_delete_household(self):
        admin_user = UserFactory()
        household = HouseholdFactory()
        add_member(household, admin_user, role=HouseholdMembership.Role.ADMIN)
        client = authed_client(admin_user)
        response = client.delete(f"/api/households/{household.id}/")
        assert response.status_code == 403
        assert Household.objects.filter(id=household.id).exists()

    def test_unauthenticated_request_is_rejected(self):
        household = HouseholdFactory()
        client = APIClient()
        response = client.get(f"/api/households/{household.id}/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestMembers:
    def test_list_members(self):
        owner = UserFactory()
        household = HouseholdFactory()
        add_member(household, owner, role=HouseholdMembership.Role.OWNER)
        add_member(household, UserFactory(), role=HouseholdMembership.Role.MEMBER)

        client = authed_client(owner)
        response = client.get(f"/api/households/{household.id}/members/")
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_non_member_cannot_list_members(self):
        household = HouseholdFactory()
        add_member(household, UserFactory(), role=HouseholdMembership.Role.OWNER)
        client = authed_client(UserFactory())
        response = client.get(f"/api/households/{household.id}/members/")
        assert response.status_code == 404

    def test_admin_can_remove_regular_member(self):
        admin_user = UserFactory()
        target = UserFactory()
        household = HouseholdFactory()
        add_member(household, admin_user, role=HouseholdMembership.Role.ADMIN)
        add_member(household, target, role=HouseholdMembership.Role.MEMBER)

        client = authed_client(admin_user)
        response = client.delete(f"/api/households/{household.id}/members/{target.id}/")
        assert response.status_code == 204
        assert not HouseholdMembership.objects.filter(household=household, user=target).exists()

    def test_regular_member_cannot_remove_another_member(self):
        member = UserFactory()
        target = UserFactory()
        household = HouseholdFactory()
        add_member(household, member, role=HouseholdMembership.Role.MEMBER)
        add_member(household, target, role=HouseholdMembership.Role.MEMBER)

        client = authed_client(member)
        response = client.delete(f"/api/households/{household.id}/members/{target.id}/")
        assert response.status_code == 403
        assert HouseholdMembership.objects.filter(household=household, user=target).exists()

    def test_owner_cannot_be_removed(self):
        admin_user = UserFactory()
        owner = UserFactory()
        household = HouseholdFactory()
        add_member(household, admin_user, role=HouseholdMembership.Role.ADMIN)
        add_member(household, owner, role=HouseholdMembership.Role.OWNER)

        client = authed_client(admin_user)
        response = client.delete(f"/api/households/{household.id}/members/{owner.id}/")
        assert response.status_code == 400
        assert HouseholdMembership.objects.filter(household=household, user=owner).exists()


@pytest.mark.django_db
class TestLeaveHousehold:
    def test_member_can_leave(self):
        user = UserFactory()
        household = HouseholdFactory()
        add_member(household, UserFactory(), role=HouseholdMembership.Role.OWNER)
        add_member(household, user, role=HouseholdMembership.Role.MEMBER)

        client = authed_client(user)
        response = client.post(f"/api/households/{household.id}/leave/")
        assert response.status_code == 204
        assert not HouseholdMembership.objects.filter(household=household, user=user).exists()

    def test_sole_owner_leaving_deletes_household(self):
        user = UserFactory()
        household = HouseholdFactory()
        add_member(household, user, role=HouseholdMembership.Role.OWNER)

        client = authed_client(user)
        response = client.post(f"/api/households/{household.id}/leave/")
        assert response.status_code == 204
        assert not Household.objects.filter(id=household.id).exists()

    def test_owner_with_other_members_cannot_leave_directly(self):
        user = UserFactory()
        household = HouseholdFactory()
        add_member(household, user, role=HouseholdMembership.Role.OWNER)
        add_member(household, UserFactory(), role=HouseholdMembership.Role.MEMBER)

        client = authed_client(user)
        response = client.post(f"/api/households/{household.id}/leave/")
        assert response.status_code == 400
        assert HouseholdMembership.objects.filter(household=household, user=user).exists()


@pytest.mark.django_db
class TestInvitations:
    def test_admin_can_invite(self):
        admin_user = UserFactory()
        household = HouseholdFactory()
        add_member(household, admin_user, role=HouseholdMembership.Role.ADMIN)

        client = authed_client(admin_user)
        response = client.post(
            f"/api/households/{household.id}/invitations/", {"email": "New@Example.com"}
        )
        assert response.status_code == 201
        assert response.data["email"] == "new@example.com"
        assert Invitation.objects.filter(household=household, email="new@example.com").exists()

    def test_regular_member_cannot_invite(self):
        member = UserFactory()
        household = HouseholdFactory()
        add_member(household, member, role=HouseholdMembership.Role.MEMBER)

        client = authed_client(member)
        response = client.post(
            f"/api/households/{household.id}/invitations/", {"email": "new@example.com"}
        )
        assert response.status_code == 403

    def test_cannot_invite_existing_member(self):
        admin_user = UserFactory()
        existing = UserFactory(email="existing@example.com")
        household = HouseholdFactory()
        add_member(household, admin_user, role=HouseholdMembership.Role.ADMIN)
        add_member(household, existing, role=HouseholdMembership.Role.MEMBER)

        client = authed_client(admin_user)
        response = client.post(
            f"/api/households/{household.id}/invitations/", {"email": "existing@example.com"}
        )
        assert response.status_code == 400

    def test_reinviting_updates_existing_pending_invitation(self):
        admin_user = UserFactory()
        household = HouseholdFactory()
        add_member(household, admin_user, role=HouseholdMembership.Role.ADMIN)
        first = InvitationFactory(household=household, email="dup@example.com", invited_by=admin_user)

        client = authed_client(admin_user)
        response = client.post(
            f"/api/households/{household.id}/invitations/", {"email": "dup@example.com"}
        )
        assert response.status_code == 201
        assert Invitation.objects.filter(
            household=household, email="dup@example.com", status=Invitation.Status.PENDING
        ).count() == 1
        assert response.data["token"] == first.token

    def test_admin_can_list_invitations(self):
        admin_user = UserFactory()
        household = HouseholdFactory()
        add_member(household, admin_user, role=HouseholdMembership.Role.ADMIN)
        InvitationFactory.create_batch(2, household=household, invited_by=admin_user)

        client = authed_client(admin_user)
        response = client.get(f"/api/households/{household.id}/invitations/")
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_accept_invitation_creates_membership(self):
        household = HouseholdFactory()
        invitee = UserFactory(email="invitee@example.com")
        invitation = InvitationFactory(household=household, email="invitee@example.com")

        client = authed_client(invitee)
        response = client.post(f"/api/invitations/{invitation.token}/accept/")
        assert response.status_code == 200
        assert HouseholdMembership.objects.filter(household=household, user=invitee).exists()
        invitation.refresh_from_db()
        assert invitation.status == Invitation.Status.ACCEPTED

    def test_accept_invitation_wrong_email_is_rejected(self):
        household = HouseholdFactory()
        wrong_user = UserFactory(email="someone-else@example.com")
        invitation = InvitationFactory(household=household, email="invitee@example.com")

        client = authed_client(wrong_user)
        response = client.post(f"/api/invitations/{invitation.token}/accept/")
        assert response.status_code == 403
        assert not HouseholdMembership.objects.filter(household=household, user=wrong_user).exists()

    def test_accept_expired_invitation_is_rejected(self):
        household = HouseholdFactory()
        invitee = UserFactory(email="invitee@example.com")
        invitation = InvitationFactory(
            household=household,
            email="invitee@example.com",
            expires_at=timezone.now() - timedelta(days=1),
        )

        client = authed_client(invitee)
        response = client.post(f"/api/invitations/{invitation.token}/accept/")
        assert response.status_code == 400
        invitation.refresh_from_db()
        assert invitation.status == Invitation.Status.EXPIRED

    def test_decline_invitation(self):
        household = HouseholdFactory()
        invitee = UserFactory(email="invitee@example.com")
        invitation = InvitationFactory(household=household, email="invitee@example.com")

        client = authed_client(invitee)
        response = client.post(f"/api/invitations/{invitation.token}/decline/")
        assert response.status_code == 204
        invitation.refresh_from_db()
        assert invitation.status == Invitation.Status.DECLINED
        assert not HouseholdMembership.objects.filter(household=household, user=invitee).exists()

    def test_unknown_token_returns_404(self):
        client = authed_client(UserFactory())
        response = client.post("/api/invitations/not-a-real-token/accept/")
        assert response.status_code == 404
