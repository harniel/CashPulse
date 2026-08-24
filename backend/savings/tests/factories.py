import datetime

import factory

from savings.models import SavingsGoal
from users.tests.factories import UserFactory


class SavingsGoalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SavingsGoal

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Goal {n}")
    target_amount = "1200.00"
    target_date = factory.LazyFunction(
        lambda: datetime.date.today() + datetime.timedelta(days=365)
    )
