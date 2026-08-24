"""
Business logic for transactions — account/household authorization that
spans models, per Section 9 of the blueprint. Shape validation (transfer
vs. category, category kind matching) lives in both the serializer (clean
400s) and Transaction.clean() (defense in depth for non-API callers).
"""

from rest_framework.exceptions import PermissionDenied, ValidationError

from audit import services as audit
from households.models import HouseholdMembership

from .models import Transaction


def _validate_account_ownership(owner, account, field_name="account"):
    if account is not None and account.user_id != owner.id:
        raise ValidationError({field_name: "You don't have access to that account."})


def _validate_household_membership(user, household):
    if household is None:
        return
    if not HouseholdMembership.objects.filter(user=user, household=household).exists():
        raise PermissionDenied("You're not a member of that household.")


def create_transaction(user, **data):
    account = data.get("account")
    to_account = data.get("to_account")
    household = data.get("household")

    _validate_account_ownership(user, account)
    _validate_account_ownership(user, to_account, field_name="to_account")
    _validate_household_membership(user, household)

    data.setdefault("currency", account.currency if account else "PHP")

    transaction = Transaction(user=user, **data)
    transaction.save()
    audit.log(
        user=user,
        household=transaction.household,
        action="create",
        entity_type="Transaction",
        entity_id=transaction.id,
        metadata=audit.full_snapshot(transaction),
    )
    return transaction


def update_transaction(transaction, actor, **data):
    # The owner of the money never changes on edit — even when a fellow
    # household member is the one editing a shared transaction, "account"
    # and "to_account" must still belong to whoever the transaction is
    # already attributed to. `actor` (who's making this specific edit) can
    # still differ from `owner` — that's exactly who the audit entry
    # needs to name.
    owner = transaction.user
    account = data.get("account", transaction.account)
    to_account = data.get("to_account", transaction.to_account)
    household = data.get("household", transaction.household)

    _validate_account_ownership(owner, account)
    _validate_account_ownership(owner, to_account, field_name="to_account")
    _validate_household_membership(owner, household)

    diff = audit.field_diff(transaction, data)
    for field, value in data.items():
        setattr(transaction, field, value)
    transaction.save()
    if diff:
        audit.log(
            user=actor,
            household=transaction.household,
            action="update",
            entity_type="Transaction",
            entity_id=transaction.id,
            metadata=diff,
        )
    return transaction


def delete_transaction(transaction, actor):
    audit.log(
        user=actor,
        household=transaction.household,
        action="delete",
        entity_type="Transaction",
        entity_id=transaction.id,
        metadata=audit.full_snapshot(transaction),
    )
    transaction.delete()
