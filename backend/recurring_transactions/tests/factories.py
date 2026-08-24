import datetime

import factory

from accounts.tests.factories import AccountFactory
from recurring_transactions.models import RecurringTransaction
from transactions.tests.factories import CategoryFactory
from users.tests.factories import UserFactory


class RecurringTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RecurringTransaction

    user = factory.SubFactory(UserFactory)
    account = factory.SubFactory(AccountFactory, user=factory.SelfAttribute("..user"))
    category = factory.SubFactory(CategoryFactory, user=factory.SelfAttribute("..user"))
    type = RecurringTransaction.Type.EXPENSE
    amount = "50.00"
    frequency = RecurringTransaction.Frequency.MONTHLY
    next_run_date = factory.LazyFunction(datetime.date.today)
    description = factory.Sequence(lambda n: f"Recurring {n}")
