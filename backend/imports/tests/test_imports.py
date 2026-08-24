import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from accounts.tests.factories import AccountFactory
from categories.models import Category
from imports.models import ImportBatch, ImportRow
from imports.services import confirm_batch, create_batch
from transactions.models import Transaction
from users.tests.factories import UserFactory

TODAY = datetime.date.today()


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def csv_file(rows, header="Date,Description,Amount", name="statement.csv"):
    content = header + "\n" + "\n".join(rows) + "\n"
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


BASIC_COLUMNS = {
    "date_column": "Date",
    "description_column": "Description",
    "amount_column": "Amount",
}


@pytest.mark.django_db
class TestUpload:
    def test_successful_upload_stages_rows(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        file = csv_file(["2026-08-01,Groceries,-50.00", "2026-08-02,Salary,2000.00"])
        response = client.post(
            "/api/imports/", {"file": file, "account": str(account.id), **BASIC_COLUMNS}, format="multipart"
        )
        assert response.status_code == 201
        batch = ImportBatch.objects.get(id=response.data["id"])
        assert batch.row_count == 2
        assert batch.rows.filter(status=ImportRow.Status.PENDING).count() == 2

    def test_rejects_non_csv_extension(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        file = SimpleUploadedFile("statement.txt", b"Date,Description,Amount\n", content_type="text/plain")
        response = client.post(
            "/api/imports/", {"file": file, "account": str(account.id), **BASIC_COLUMNS}, format="multipart"
        )
        assert response.status_code == 400

    def test_rejects_missing_required_column(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        file = csv_file(["2026-08-01,-50.00"], header="Date,Amount")
        response = client.post(
            "/api/imports/", {"file": file, "account": str(account.id), **BASIC_COLUMNS}, format="multipart"
        )
        assert response.status_code == 400

    def test_rejects_empty_file(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        file = csv_file([])
        response = client.post(
            "/api/imports/", {"file": file, "account": str(account.id), **BASIC_COLUMNS}, format="multipart"
        )
        assert response.status_code == 400

    def test_rejects_file_over_size_limit(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        file = csv_file(["2026-08-01,Groceries,-50.00"])
        with patch("imports.services.MAX_FILE_SIZE_BYTES", 5):
            response = client.post(
                "/api/imports/",
                {"file": file, "account": str(account.id), **BASIC_COLUMNS},
                format="multipart",
            )
        assert response.status_code == 400

    def test_rejects_too_many_rows(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        rows = [f"2026-08-01,Row {i},-1.00" for i in range(501)]
        file = csv_file(rows)
        response = client.post(
            "/api/imports/", {"file": file, "account": str(account.id), **BASIC_COLUMNS}, format="multipart"
        )
        assert response.status_code == 400

    def test_unparseable_date_row_is_marked_failed(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        file = csv_file(["not-a-date,Groceries,-50.00"])
        response = client.post(
            "/api/imports/", {"file": file, "account": str(account.id), **BASIC_COLUMNS}, format="multipart"
        )
        batch = ImportBatch.objects.get(id=response.data["id"])
        row = batch.rows.first()
        assert row.status == ImportRow.Status.FAILED
        assert "date" in row.error.lower()

    def test_unparseable_amount_row_is_marked_failed(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        client = authed_client(user)

        file = csv_file(["2026-08-01,Groceries,N/A"])
        response = client.post(
            "/api/imports/", {"file": file, "account": str(account.id), **BASIC_COLUMNS}, format="multipart"
        )
        batch = ImportBatch.objects.get(id=response.data["id"])
        row = batch.rows.first()
        assert row.status == ImportRow.Status.FAILED
        assert "amount" in row.error.lower()

    def test_row_within_two_days_of_existing_transaction_is_flagged_duplicate(self):
        user = UserFactory()
        account = AccountFactory(user=user)

        category = Category.objects.filter(is_system=True, kind="expense").first()
        Transaction.objects.create(
            user=user, account=account, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("50.00"), date=datetime.date(2026, 8, 2),
        )

        client = authed_client(user)
        file = csv_file(["2026-08-01,Groceries,-50.00"])  # 1 day apart, same amount
        response = client.post(
            "/api/imports/", {"file": file, "account": str(account.id), **BASIC_COLUMNS}, format="multipart"
        )
        batch = ImportBatch.objects.get(id=response.data["id"])
        assert batch.rows.first().is_duplicate is True

    def test_row_outside_duplicate_window_is_not_flagged(self):
        user = UserFactory()
        account = AccountFactory(user=user)

        category = Category.objects.filter(is_system=True, kind="expense").first()
        Transaction.objects.create(
            user=user, account=account, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("50.00"), date=datetime.date(2026, 8, 10),
        )

        client = authed_client(user)
        file = csv_file(["2026-08-01,Groceries,-50.00"])  # 9 days apart
        response = client.post(
            "/api/imports/", {"file": file, "account": str(account.id), **BASIC_COLUMNS}, format="multipart"
        )
        batch = ImportBatch.objects.get(id=response.data["id"])
        assert batch.rows.first().is_duplicate is False

    def test_cannot_upload_against_another_users_account(self):
        user = UserFactory()
        other_account = AccountFactory(user=UserFactory())
        client = authed_client(user)

        file = csv_file(["2026-08-01,Groceries,-50.00"])
        response = client.post(
            "/api/imports/",
            {"file": file, "account": str(other_account.id), **BASIC_COLUMNS},
            format="multipart",
        )
        assert response.status_code == 400

    def test_unauthenticated_request_is_rejected(self):
        client = APIClient()
        response = client.post("/api/imports/", {}, format="multipart")
        assert response.status_code == 401


@pytest.mark.django_db
class TestPreview:
    def test_preview_lists_rows(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        batch = create_batch(
            user=user,
            account=account,
            uploaded_file=csv_file(["2026-08-01,Groceries,-50.00", "2026-08-02,Salary,2000.00"]),
            **BASIC_COLUMNS,
        )
        client = authed_client(user)
        response = client.get(f"/api/imports/{batch.id}/preview/")
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_cannot_preview_another_users_batch(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        batch = create_batch(
            user=user, account=account, uploaded_file=csv_file(["2026-08-01,Groceries,-50.00"]), **BASIC_COLUMNS
        )
        client = authed_client(UserFactory())
        response = client.get(f"/api/imports/{batch.id}/preview/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestConfirm:
    def test_confirm_with_no_row_ids_imports_all_non_duplicates(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        batch = create_batch(
            user=user,
            account=account,
            uploaded_file=csv_file(["2026-08-01,Groceries,-50.00", "2026-08-02,Salary,2000.00"]),
            **BASIC_COLUMNS,
        )
        client = authed_client(user)
        response = client.post(f"/api/imports/{batch.id}/confirm/", {}, format="json")
        assert response.status_code == 200
        assert response.data["imported_count"] == 2

        expense_row, income_row = batch.rows.order_by("created_at")
        assert expense_row.status == ImportRow.Status.IMPORTED
        assert expense_row.transaction.type == Transaction.Type.EXPENSE
        assert expense_row.transaction.amount == Decimal("50.00")
        assert expense_row.transaction.category.name == "Other Expense"
        assert income_row.transaction.type == Transaction.Type.INCOME
        assert income_row.transaction.amount == Decimal("2000.00")
        assert income_row.transaction.category.name == "Other Income"

        batch.refresh_from_db()
        assert batch.status == ImportBatch.Status.CONFIRMED

    def test_duplicate_rows_are_skipped_by_default(self):
        user = UserFactory()
        account = AccountFactory(user=user)

        category = Category.objects.filter(is_system=True, kind="expense").first()
        Transaction.objects.create(
            user=user, account=account, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("50.00"), date=datetime.date(2026, 8, 2),
        )
        batch = create_batch(
            user=user, account=account, uploaded_file=csv_file(["2026-08-01,Groceries,-50.00"]), **BASIC_COLUMNS
        )
        imported = confirm_batch(batch)
        assert imported == []
        row = batch.rows.first()
        assert row.status == ImportRow.Status.SKIPPED

    def test_explicit_row_ids_can_include_a_duplicate(self):
        user = UserFactory()
        account = AccountFactory(user=user)

        category = Category.objects.filter(is_system=True, kind="expense").first()
        Transaction.objects.create(
            user=user, account=account, category=category, type=Transaction.Type.EXPENSE,
            amount=Decimal("50.00"), date=datetime.date(2026, 8, 2),
        )
        batch = create_batch(
            user=user, account=account, uploaded_file=csv_file(["2026-08-01,Groceries,-50.00"]), **BASIC_COLUMNS
        )
        duplicate_row = batch.rows.first()
        assert duplicate_row.is_duplicate is True

        imported = confirm_batch(batch, row_ids=[duplicate_row.id])
        assert len(imported) == 1
        duplicate_row.refresh_from_db()
        assert duplicate_row.status == ImportRow.Status.IMPORTED

    def test_cannot_confirm_twice(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        batch = create_batch(
            user=user, account=account, uploaded_file=csv_file(["2026-08-01,Groceries,-50.00"]), **BASIC_COLUMNS
        )
        confirm_batch(batch)
        with pytest.raises(Exception):
            confirm_batch(batch)

    def test_unknown_row_id_is_rejected(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        batch = create_batch(
            user=user, account=account, uploaded_file=csv_file(["2026-08-01,Groceries,-50.00"]), **BASIC_COLUMNS
        )
        with pytest.raises(Exception):
            confirm_batch(batch, row_ids=["00000000-0000-0000-0000-000000000000"])

    def test_cannot_confirm_another_users_batch(self):
        user = UserFactory()
        account = AccountFactory(user=user)
        batch = create_batch(
            user=user, account=account, uploaded_file=csv_file(["2026-08-01,Groceries,-50.00"]), **BASIC_COLUMNS
        )
        client = authed_client(UserFactory())
        response = client.post(f"/api/imports/{batch.id}/confirm/", {}, format="json")
        assert response.status_code == 404
