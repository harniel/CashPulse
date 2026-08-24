import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import AccountFactory
from audit.models import AuditLogEntry
from audit.services import field_diff, full_snapshot
from budgets.tests.factories import BudgetFactory
from categories.models import Category
from households.models import HouseholdMembership
from households.services import accept_invitation, leave_household, remove_member
from households.tests.factories import (
    HouseholdFactory,
    HouseholdMembershipFactory,
    InvitationFactory,
)
from loans.services import log_payment
from loans.tests.factories import LoanFactory
from transactions.tests.factories import CategoryFactory, TransactionFactory
from users.tests.factories import UserFactory

TODAY = datetime.date.today()


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestGenericHelpers:
    def test_full_snapshot_excludes_timestamps_and_serializes_fks(self):
        transaction = TransactionFactory()
        snapshot = full_snapshot(transaction)
        assert "created_at" not in snapshot
        assert "updated_at" not in snapshot
        assert snapshot["account"] == str(transaction.account_id)
        assert snapshot["amount"] == str(transaction.amount)

    def test_field_diff_only_includes_changed_fields(self):
        transaction = TransactionFactory(description="Old", amount=Decimal("50.00"))
        diff = field_diff(transaction, {"description": "New", "amount": Decimal("50.00")})
        assert list(diff.keys()) == ["description"]
        assert diff["description"] == {"old": "Old", "new": "New"}


@pytest.mark.django_db
class TestTransactionAudit:
    def test_create_logs_full_snapshot(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        client = authed_client(user)

        response = client.post(
            "/api/transactions/",
            {
                "account": str(AccountFactory(user=user).id),
                "category": str(category.id),
                "type": "expense",
                "amount": "42.00",
                "date": TODAY.isoformat(),
            },
        )
        assert response.status_code == 201
        entry = AuditLogEntry.objects.get(entity_type="Transaction", entity_id=response.data["id"])
        assert entry.action == "create"
        assert entry.user_id == user.id
        assert entry.metadata["amount"] == "42.00"

    def test_update_logs_diff_with_actor_not_owner(self):
        owner = UserFactory()
        other_member = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(user=owner, household=household, role=HouseholdMembership.Role.OWNER)
        HouseholdMembershipFactory(user=other_member, household=household, role=HouseholdMembership.Role.MEMBER)
        transaction = TransactionFactory(user=owner, household=household, description="Rent")

        client = authed_client(other_member)
        response = client.patch(
            f"/api/transactions/{transaction.id}/", {"description": "Rent (August)"}
        )
        assert response.status_code == 200

        entry = AuditLogEntry.objects.get(
            entity_type="Transaction", entity_id=transaction.id, action="update"
        )
        assert entry.user_id == other_member.id  # the actor, not the owner
        assert entry.metadata["description"] == {"old": "Rent", "new": "Rent (August)"}

    def test_no_op_update_creates_no_audit_entry(self):
        user = UserFactory()
        transaction = TransactionFactory(user=user, description="Same")
        client = authed_client(user)

        client.patch(f"/api/transactions/{transaction.id}/", {"description": "Same"})
        assert not AuditLogEntry.objects.filter(
            entity_type="Transaction", entity_id=transaction.id, action="update"
        ).exists()

    def test_delete_logs_full_snapshot_before_removal(self):
        user = UserFactory()
        transaction = TransactionFactory(user=user, amount=Decimal("77.00"))
        transaction_id = transaction.id
        client = authed_client(user)

        response = client.delete(f"/api/transactions/{transaction_id}/")
        assert response.status_code == 204
        entry = AuditLogEntry.objects.get(entity_type="Transaction", entity_id=transaction_id, action="delete")
        assert entry.metadata["amount"] == "77.00"


@pytest.mark.django_db
class TestBudgetAudit:
    def test_create_update_delete_all_logged(self):
        user = UserFactory()
        category = CategoryFactory(user=user, kind=Category.Kind.EXPENSE)
        budget = BudgetFactory(user=user, category=category, month=TODAY.replace(day=1), amount=Decimal("100.00"))
        client = authed_client(user)

        response = client.patch(f"/api/budgets/{budget.id}/", {"amount": "150.00"})
        assert response.status_code == 200
        update_entry = AuditLogEntry.objects.get(entity_type="Budget", entity_id=budget.id, action="update")
        assert update_entry.metadata["amount"] == {"old": "100.00", "new": "150.00"}

        response = client.delete(f"/api/budgets/{budget.id}/")
        assert response.status_code == 204
        assert AuditLogEntry.objects.filter(entity_type="Budget", entity_id=budget.id, action="delete").exists()


@pytest.mark.django_db
class TestLoanPaymentAudit:
    def test_log_payment_creates_audit_entry(self):
        loan = LoanFactory(principal=Decimal("1000.00"), interest_rate=Decimal("0.000"), term_months=12)
        payment = log_payment(loan, date_=TODAY, amount=Decimal("100.00"), is_extra=True)
        entry = AuditLogEntry.objects.get(entity_type="LoanPayment", entity_id=payment.id)
        assert entry.action == "create"
        assert entry.user_id == loan.user_id
        assert entry.metadata["amount"] == "100.00"


@pytest.mark.django_db
class TestHouseholdMembershipAudit:
    def test_accept_invitation_logs_create(self):
        household = HouseholdFactory()
        invitee = UserFactory(email="invitee@example.com")
        invitation = InvitationFactory(household=household, email="invitee@example.com")

        membership = accept_invitation(invitation, invitee)
        entry = AuditLogEntry.objects.get(entity_type="HouseholdMembership", entity_id=membership.id)
        assert entry.action == "create"
        assert entry.user_id == invitee.id
        assert entry.household_id == household.id

    def test_remove_member_logs_delete_with_admin_as_actor(self):
        admin_user = UserFactory()
        target = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(user=admin_user, household=household, role=HouseholdMembership.Role.ADMIN)
        target_membership = HouseholdMembershipFactory(
            user=target, household=household, role=HouseholdMembership.Role.MEMBER
        )

        remove_member(household=household, actor=admin_user, target_user=target)
        entry = AuditLogEntry.objects.get(
            entity_type="HouseholdMembership", entity_id=target_membership.id, action="delete"
        )
        assert entry.user_id == admin_user.id
        assert entry.metadata["removed_user"] == str(target.id)

    def test_leave_household_logs_self_removal(self):
        owner = UserFactory()
        member = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(user=owner, household=household, role=HouseholdMembership.Role.OWNER)
        member_membership = HouseholdMembershipFactory(
            user=member, household=household, role=HouseholdMembership.Role.MEMBER
        )

        leave_household(household=household, user=member)
        entry = AuditLogEntry.objects.get(
            entity_type="HouseholdMembership", entity_id=member_membership.id, action="delete"
        )
        assert entry.user_id == member.id
        assert entry.metadata["self_removed"] is True


@pytest.mark.django_db
class TestAuditLogEntrySurvivesHouseholdDeletion:
    def test_household_deletion_sets_null_rather_than_cascading(self):
        household = HouseholdFactory()
        user = UserFactory()
        HouseholdMembershipFactory(user=user, household=household, role=HouseholdMembership.Role.OWNER)
        entry = AuditLogEntry.objects.create(
            user=user, household=household, action="create", entity_type="Test", entity_id=household.id
        )

        household.delete()
        entry.refresh_from_db()
        assert entry.household_id is None
