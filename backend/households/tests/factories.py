import factory

from households.models import Household, HouseholdMembership, Invitation
from users.tests.factories import UserFactory


class HouseholdFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Household

    name = factory.Sequence(lambda n: f"Household {n}")
    created_by = factory.SubFactory(UserFactory)


class HouseholdMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HouseholdMembership

    user = factory.SubFactory(UserFactory)
    household = factory.SubFactory(HouseholdFactory)
    role = HouseholdMembership.Role.MEMBER


class InvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invitation

    household = factory.SubFactory(HouseholdFactory)
    email = factory.Sequence(lambda n: f"invitee{n}@example.com")
    invited_by = factory.SubFactory(UserFactory)
