import factory

from accounts.models import Account
from users.tests.factories import UserFactory


class AccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Account

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Account {n}")
    account_type = Account.AccountType.BANK
    currency = "PHP"
