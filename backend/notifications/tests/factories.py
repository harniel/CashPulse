import factory

from notifications.models import Notification
from users.tests.factories import UserFactory


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    user = factory.SubFactory(UserFactory)
    type = Notification.Type.BUDGET_EXCEEDED
    payload = factory.LazyFunction(dict)
