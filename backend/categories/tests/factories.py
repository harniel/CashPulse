import factory

from categories.models import Category
from users.tests.factories import UserFactory


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Category {n}")
    kind = Category.Kind.EXPENSE
    is_system = False


class SystemCategoryFactory(CategoryFactory):
    user = None
    is_system = True
