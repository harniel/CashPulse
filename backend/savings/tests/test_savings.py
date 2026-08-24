import datetime
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from households.models import HouseholdMembership
from households.tests.factories import HouseholdFactory, HouseholdMembershipFactory
from savings.models import SavingsGoal
from savings.services import (
    is_behind_pace,
    log_contribution,
    progress_pct,
    required_monthly_contribution,
    total_contributed,
)
from savings.tests.factories import SavingsGoalFactory
from users.tests.factories import UserFactory

TODAY = datetime.date.today()


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def backdate(goal, days_ago):
    """SavingsGoal.created_at is auto_now_add — bypass it with a direct
    .update() (only affects INSERT, not later UPDATEs) so pacing tests can
    control "how much time has elapsed since this goal was created"."""
    when = timezone.make_aware(
        datetime.datetime.combine(TODAY - datetime.timedelta(days=days_ago), datetime.time())
    )
    SavingsGoal.objects.filter(id=goal.id).update(created_at=when)
    goal.refresh_from_db()
    return goal


@pytest.mark.django_db
class TestSavingsGoalCRUD:
    def test_create_personal_goal(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.post(
            "/api/savings-goals/",
            {
                "name": "Emergency Fund",
                "target_amount": "50000.00",
                "target_date": (TODAY + datetime.timedelta(days=365)).isoformat(),
            },
        )
        assert response.status_code == 201
        goal = SavingsGoal.objects.get(id=response.data["id"])
        assert goal.user_id == user.id
        assert Decimal(response.data["total_contributed"]) == Decimal("0")

    def test_target_amount_must_be_positive(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.post(
            "/api/savings-goals/",
            {
                "name": "Bad Goal",
                "target_amount": "0.00",
                "target_date": (TODAY + datetime.timedelta(days=30)).isoformat(),
            },
        )
        assert response.status_code == 400

    def test_create_shared_goal_requires_membership(self):
        user = UserFactory()
        household = HouseholdFactory()
        client = authed_client(user)
        response = client.post(
            "/api/savings-goals/",
            {
                "name": "Vacation",
                "household": str(household.id),
                "target_amount": "20000.00",
                "target_date": (TODAY + datetime.timedelta(days=180)).isoformat(),
            },
        )
        assert response.status_code == 403

    def test_create_shared_goal_as_member(self):
        user = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=user, household=household, role=HouseholdMembership.Role.OWNER
        )
        client = authed_client(user)
        response = client.post(
            "/api/savings-goals/",
            {
                "name": "Vacation",
                "household": str(household.id),
                "target_amount": "20000.00",
                "target_date": (TODAY + datetime.timedelta(days=180)).isoformat(),
            },
        )
        assert response.status_code == 201

    def test_cannot_retrieve_another_users_personal_goal(self):
        goal = SavingsGoalFactory()
        client = authed_client(UserFactory())
        response = client.get(f"/api/savings-goals/{goal.id}/")
        assert response.status_code == 404

    def test_shared_goal_visible_to_other_household_member(self):
        owner = UserFactory()
        other_member = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(
            user=owner, household=household, role=HouseholdMembership.Role.OWNER
        )
        HouseholdMembershipFactory(
            user=other_member, household=household, role=HouseholdMembership.Role.MEMBER
        )
        goal = SavingsGoalFactory(user=owner, household=household)

        client = authed_client(other_member)
        response = client.get(f"/api/savings-goals/{goal.id}/")
        assert response.status_code == 200

    def test_unauthenticated_request_is_rejected(self):
        goal = SavingsGoalFactory()
        client = APIClient()
        response = client.get(f"/api/savings-goals/{goal.id}/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestContributions:
    def test_log_contribution_via_api(self):
        user = UserFactory()
        goal = SavingsGoalFactory(user=user, target_amount=Decimal("1000.00"))
        client = authed_client(user)

        response = client.post(
            f"/api/savings-goals/{goal.id}/contributions/",
            {"date": TODAY.isoformat(), "amount": "250.00"},
        )
        assert response.status_code == 201
        assert total_contributed(goal) == Decimal("250.00")

    def test_list_contributions(self):
        goal = SavingsGoalFactory()
        log_contribution(goal, date_=TODAY, amount=Decimal("100.00"))
        log_contribution(goal, date_=TODAY, amount=Decimal("50.00"))

        client = authed_client(goal.user)
        response = client.get(f"/api/savings-goals/{goal.id}/contributions/")
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_contribution_amount_must_be_positive(self):
        goal = SavingsGoalFactory()
        with pytest.raises(Exception):
            log_contribution(goal, date_=TODAY, amount=Decimal("0.00"))

    def test_contribution_before_goal_creation_is_rejected(self):
        goal = SavingsGoalFactory()
        with pytest.raises(Exception):
            log_contribution(
                goal, date_=TODAY - datetime.timedelta(days=3650), amount=Decimal("10.00")
            )

    def test_overcontribution_beyond_target_is_allowed(self):
        goal = SavingsGoalFactory(target_amount=Decimal("100.00"))
        log_contribution(goal, date_=TODAY, amount=Decimal("500.00"))
        assert total_contributed(goal) == Decimal("500.00")
        assert progress_pct(goal) == Decimal("500.00")

    def test_cannot_log_contribution_on_another_users_goal(self):
        goal = SavingsGoalFactory()
        client = authed_client(UserFactory())
        response = client.post(
            f"/api/savings-goals/{goal.id}/contributions/",
            {"date": TODAY.isoformat(), "amount": "10.00"},
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestProgressAndPace:
    def test_progress_pct(self):
        goal = SavingsGoalFactory(target_amount=Decimal("1000.00"))
        log_contribution(goal, date_=TODAY, amount=Decimal("250.00"))
        assert progress_pct(goal) == Decimal("25.00")

    def test_required_monthly_contribution_with_no_progress(self):
        goal = SavingsGoalFactory(
            target_amount=Decimal("1200.00"), target_date=TODAY + datetime.timedelta(days=365)
        )
        required = required_monthly_contribution(goal, as_of=TODAY)
        assert required == Decimal("100.00")

    def test_required_monthly_contribution_is_zero_once_met(self):
        goal = SavingsGoalFactory(target_amount=Decimal("100.00"))
        log_contribution(goal, date_=TODAY, amount=Decimal("150.00"))
        assert required_monthly_contribution(goal, as_of=TODAY) == Decimal("0.00")

    def test_required_monthly_contribution_is_none_past_target_date(self):
        goal = SavingsGoalFactory(target_date=TODAY - datetime.timedelta(days=1))
        assert required_monthly_contribution(goal, as_of=TODAY) is None

    def test_not_behind_pace_on_creation_day(self):
        goal = SavingsGoalFactory(target_amount=Decimal("1000.00"))
        assert is_behind_pace(goal, as_of=TODAY) is False

    def test_behind_pace_when_underfunded_partway_through(self):
        goal = SavingsGoalFactory(
            target_amount=Decimal("1000.00"), target_date=TODAY + datetime.timedelta(days=50)
        )
        backdate(goal, days_ago=50)  # total window = 100 days, we're at day 50 (halfway)
        # Expected by now: ~500. Contributed far less -> behind.
        log_contribution(goal, date_=TODAY, amount=Decimal("100.00"))
        assert is_behind_pace(goal, as_of=TODAY) is True

    def test_not_behind_pace_when_on_track(self):
        goal = SavingsGoalFactory(
            target_amount=Decimal("1000.00"), target_date=TODAY + datetime.timedelta(days=50)
        )
        backdate(goal, days_ago=50)
        log_contribution(goal, date_=TODAY, amount=Decimal("600.00"))
        assert is_behind_pace(goal, as_of=TODAY) is False

    def test_not_behind_pace_once_goal_is_fully_funded(self):
        goal = SavingsGoalFactory(
            target_amount=Decimal("1000.00"), target_date=TODAY + datetime.timedelta(days=50)
        )
        backdate(goal, days_ago=50)
        log_contribution(goal, date_=TODAY, amount=Decimal("1000.00"))
        assert is_behind_pace(goal, as_of=TODAY) is False

    def test_behind_pace_is_none_when_target_date_not_after_creation(self):
        goal = SavingsGoalFactory(target_date=TODAY)
        backdate(goal, days_ago=0)
        assert is_behind_pace(goal, as_of=TODAY) is None
