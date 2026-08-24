import datetime

import factory

from accounts.tests.factories import AccountFactory
from categories.models import Category
from transactions.models import Transaction
from users.tests.factories import UserFactory


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    kind = Category.Kind.EXPENSE
    user = factory.SubFactory(UserFactory)


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    user = factory.SubFactory(UserFactory)
    account = factory.SubFactory(AccountFactory, user=factory.SelfAttribute("..user"))
    category = factory.SubFactory(CategoryFactory, user=factory.SelfAttribute("..user"))
    type = Transaction.Type.EXPENSE
    amount = "100.00"
    date = factory.LazyFunction(datetime.date.today)
    description = factory.Sequence(lambda n: f"Transaction {n}")
