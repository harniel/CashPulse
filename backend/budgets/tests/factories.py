import datetime

import factory

from budgets.models import Budget
from transactions.tests.factories import CategoryFactory
from users.tests.factories import UserFactory


def _first_of_this_month():
    today = datetime.date.today()
    return today.replace(day=1)


class BudgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Budget

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory, user=factory.SelfAttribute("..user"))
    month = factory.LazyFunction(_first_of_this_month)
    amount = "500.00"
