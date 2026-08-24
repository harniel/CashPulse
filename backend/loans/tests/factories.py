import datetime

import factory

from loans.models import Loan
from users.tests.factories import UserFactory


class LoanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Loan

    user = factory.SubFactory(UserFactory)
    lender = factory.Sequence(lambda n: f"Lender {n}")
    principal = "10000.00"
    interest_rate = "12.000"
    term_months = 12
    start_date = factory.LazyFunction(datetime.date.today)
