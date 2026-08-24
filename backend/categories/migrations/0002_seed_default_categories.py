from django.db import migrations

# (name, kind, [children])
DEFAULT_CATEGORIES = [
    ("Salary", "income", []),
    ("Freelance", "income", []),
    ("Business", "income", []),
    ("Investment", "income", []),
    ("Other Income", "income", []),
    ("Housing", "expense", ["Rent/Mortgage", "Utilities", "Repairs"]),
    ("Food", "expense", ["Groceries", "Restaurants", "Coffee", "Delivery"]),
    ("Transportation", "expense", ["Fuel", "Public Transit", "Ride-hailing", "Parking"]),
    ("Healthcare", "expense", ["Doctor Visits", "Medicine", "Insurance"]),
    ("Education", "expense", []),
    ("Shopping", "expense", []),
    ("Entertainment", "expense", []),
    ("Insurance", "expense", []),
    ("Debt Payments", "expense", []),
    ("Other Expense", "expense", []),
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    for name, kind, children in DEFAULT_CATEGORIES:
        parent, _ = Category.objects.get_or_create(
            name=name, kind=kind, parent=None, user=None,
            defaults={"is_system": True},
        )
        for child_name in children:
            Category.objects.get_or_create(
                name=child_name, kind=kind, parent=parent, user=None,
                defaults={"is_system": True},
            )


def remove_seeded_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    Category.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("categories", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, remove_seeded_categories),
    ]
