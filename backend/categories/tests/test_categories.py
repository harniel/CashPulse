import pytest
from rest_framework.test import APIClient

from categories.models import Category
from categories.tests.factories import CategoryFactory
from users.tests.factories import UserFactory


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestSeededCategories:
    """
    These run against the real 0002_seed_default_categories migration
    (pytest-django applies all migrations by default), so they're
    actually exercising the seed data, not a hand-built fixture.
    """

    def test_system_categories_exist_after_migration(self):
        assert Category.objects.filter(is_system=True).count() > 0

    def test_food_has_expected_children(self):
        food = Category.objects.get(name="Food", is_system=True)
        children = set(food.children.values_list("name", flat=True))
        assert {"Groceries", "Restaurants"}.issubset(children)

    def test_income_and_expense_categories_both_seeded(self):
        assert Category.objects.filter(is_system=True, kind="income").exists()
        assert Category.objects.filter(is_system=True, kind="expense").exists()

    def test_new_user_can_see_system_categories_immediately(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.get("/api/categories/?is_system=true")
        assert response.status_code == 200
        assert response.data["count"] > 0


@pytest.mark.django_db
class TestCategoryTreeConstraint:
    def test_can_create_child_under_system_category(self):
        user = UserFactory()
        parent = Category.objects.get(name="Entertainment", is_system=True)
        client = authed_client(user)
        response = client.post(
            "/api/categories/",
            {"name": "Streaming", "kind": "expense", "parent": str(parent.id)},
        )
        assert response.status_code == 201

    def test_cannot_create_grandchild_category(self):
        user = UserFactory()
        food = Category.objects.get(name="Food", is_system=True)
        groceries = food.children.get(name="Groceries")

        client = authed_client(user)
        response = client.post(
            "/api/categories/",
            {"name": "Organic", "kind": "expense", "parent": str(groceries.id)},
        )
        assert response.status_code == 400

    def test_child_kind_must_match_parent_kind(self):
        user = UserFactory()
        food = Category.objects.get(name="Food", is_system=True)  # expense
        client = authed_client(user)
        response = client.post(
            "/api/categories/",
            {"name": "Mismatched", "kind": "income", "parent": str(food.id)},
        )
        assert response.status_code == 400

    def test_cannot_nest_under_another_users_custom_category(self):
        owner = UserFactory()
        attacker = UserFactory()
        private_parent = CategoryFactory(user=owner, kind="expense", name="Owner's Category")

        client = authed_client(attacker)
        response = client.post(
            "/api/categories/",
            {"name": "Sneaky Child", "kind": "expense", "parent": str(private_parent.id)},
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestSystemCategoriesAreReadOnly:
    def test_cannot_update_a_system_category(self):
        user = UserFactory()
        system_cat = Category.objects.filter(is_system=True, parent=None).first()
        client = authed_client(user)
        response = client.patch(f"/api/categories/{system_cat.id}/", {"name": "Hacked"})
        assert response.status_code == 403
        system_cat.refresh_from_db()
        assert system_cat.name != "Hacked"

    def test_cannot_delete_a_system_category(self):
        user = UserFactory()
        system_cat = Category.objects.filter(is_system=True, parent=None).first()
        client = authed_client(user)
        response = client.delete(f"/api/categories/{system_cat.id}/")
        assert response.status_code == 403
        assert Category.objects.filter(id=system_cat.id).exists()

    def test_created_category_is_never_system(self):
        """
        Even if a client tries to sneak is_system=True into the payload,
        the serializer marks it read-only and the view forces False.
        """
        user = UserFactory()
        client = authed_client(user)
        response = client.post(
            "/api/categories/",
            {"name": "My Custom", "kind": "expense", "is_system": True},
        )
        assert response.status_code == 201
        category = Category.objects.get(id=response.data["id"])
        assert category.is_system is False


@pytest.mark.django_db
class TestCategoryCrossUserIsolation:
    def test_user_can_see_own_and_system_but_not_others_custom_categories(self):
        user = UserFactory()
        other = UserFactory()
        own = CategoryFactory(user=user, name="Mine", kind="expense")
        CategoryFactory(user=other, name="Not Mine", kind="expense")

        client = authed_client(user)
        response = client.get("/api/categories/")
        names = {c["name"] for c in response.data["results"]}

        assert "Mine" in names
        assert "Not Mine" not in names
        assert own.id is not None  # sanity: fixture actually persisted

    def test_cannot_retrieve_another_users_custom_category_by_id(self):
        owner = UserFactory()
        attacker = UserFactory()
        private_cat = CategoryFactory(user=owner, name="Private")

        client = authed_client(attacker)
        response = client.get(f"/api/categories/{private_cat.id}/")
        assert response.status_code == 404

    def test_cannot_delete_another_users_custom_category(self):
        owner = UserFactory()
        attacker = UserFactory()
        private_cat = CategoryFactory(user=owner, name="Private")

        client = authed_client(attacker)
        response = client.delete(f"/api/categories/{private_cat.id}/")
        assert response.status_code == 404
        assert Category.objects.filter(id=private_cat.id).exists()


@pytest.mark.django_db
class TestCategoryUniqueness:
    """
    Regression tests: a plain UniqueConstraint on (user, name, kind,
    parent) never fires for top-level categories, because `parent` is
    NULL there and SQL/Django both treat NULL as never equal to NULL —
    split into two conditional constraints in the migration that added
    these tests.
    """

    def test_duplicate_top_level_category_is_rejected(self):
        user = UserFactory()
        CategoryFactory(user=user, name="Side Hustle", kind="income", parent=None)
        client = authed_client(user)
        response = client.post(
            "/api/categories/", {"name": "Side Hustle", "kind": "income"}
        )
        assert response.status_code == 400

    def test_duplicate_subcategory_is_rejected_with_a_clean_400(self):
        # Also a regression test for the DRF EXCEPTION_HANDLER: without
        # common.exceptions.exception_handler converting the plain django
        # ValidationError that Category.save()'s full_clean() raises, this
        # used to be an unhandled 500.
        user = UserFactory()
        parent = CategoryFactory(user=user, name="Food", kind="expense", parent=None)
        CategoryFactory(user=user, name="Snacks", kind="expense", parent=parent)

        client = authed_client(user)
        response = client.post(
            "/api/categories/",
            {"name": "Snacks", "kind": "expense", "parent": str(parent.id)},
        )
        assert response.status_code == 400
