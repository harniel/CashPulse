from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimeStampedUUIDModel


class Category(TimeStampedUUIDModel):
    """
    Self-referencing one level deep: Food -> Groceries/Restaurants, but
    Groceries can't itself have children. Enforced in clean() rather
    than the database because "no grandchildren" is a business rule
    about tree shape, not a column-level constraint Postgres can express
    cleanly — application-layer validation is the right tool here.

    `user` is null for system-seeded categories (shared across every
    user, read-only via the API — see serializers.py) and set for a
    user's own custom categories.
    """

    class Kind(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )
    is_system = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["kind", "name"]
        constraints = [
            # A user's own top-level categories can't repeat by name+kind.
            # (System categories are excluded — a user might reasonably
            # want a custom "Food" alongside the system one; the app can
            # surface that as a soft warning in the UI later if needed.)
            models.UniqueConstraint(
                fields=["user", "name", "kind", "parent"],
                name="unique_category_name_per_user_per_parent",
            )
        ]

    def __str__(self):
        return f"{self.parent.name} > {self.name}" if self.parent_id else self.name

    def clean(self):
        super().clean()
        if self.parent_id and self.parent.parent_id:
            raise ValidationError(
                "Categories can only be one level deep — a child category "
                "cannot itself have a parent with a parent."
            )
        if self.parent_id and self.parent.kind != self.kind:
            raise ValidationError(
                "A category's kind (income/expense) must match its parent's."
            )
        if self.is_system and self.user_id:
            raise ValidationError("A system category cannot also belong to a user.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
