import datetime
import io

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from budgets.models import Budget
from budgets.tests.factories import BudgetFactory
from categories.models import Category
from households.tests.factories import HouseholdFactory, HouseholdMembershipFactory
from imports.models import BudgetImportBatch, BudgetImportRow
from users.tests.factories import UserFactory

THIS_MONTH = datetime.date.today().replace(day=1)
MONTH_STR = THIS_MONTH.strftime("%Y-%m")


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def xlsx_file(rows, header=("Category", "Month", "Amount", "Household"), name="budgets.xlsx"):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(list(header))
    for row in rows:
        sheet.append(list(row))
    buffer = io.BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@pytest.mark.django_db
class TestUpload:
    def test_successful_upload_stages_rows_as_create(self):
        user = UserFactory()
        client = authed_client(user)

        file = xlsx_file([("Food", MONTH_STR, 15000, "")])
        response = client.post("/api/imports/budgets/", {"file": file}, format="multipart")

        assert response.status_code == 201
        batch = BudgetImportBatch.objects.get(id=response.data["id"])
        assert batch.row_count == 1
        row = batch.rows.get()
        assert row.status == BudgetImportRow.Status.PENDING
        assert row.action == BudgetImportRow.Action.CREATE

    def test_existing_budget_stages_as_update(self):
        user = UserFactory()
        category = Category.objects.filter(is_system=True, name="Food").first()
        BudgetFactory(user=user, category=category, month=THIS_MONTH, amount="10000.00")
        client = authed_client(user)

        file = xlsx_file([("Food", MONTH_STR, 15000, "")])
        response = client.post("/api/imports/budgets/", {"file": file}, format="multipart")

        row = BudgetImportBatch.objects.get(id=response.data["id"]).rows.get()
        assert row.action == BudgetImportRow.Action.UPDATE

    def test_rejects_non_xlsx_extension(self):
        user = UserFactory()
        client = authed_client(user)

        file = SimpleUploadedFile("budgets.csv", b"Category,Month,Amount\n", content_type="text/csv")
        response = client.post("/api/imports/budgets/", {"file": file}, format="multipart")
        assert response.status_code == 400

    def test_rejects_missing_required_column(self):
        user = UserFactory()
        client = authed_client(user)

        file = xlsx_file([("Food", MONTH_STR, 15000)], header=("Category", "Month", "Notes"))
        response = client.post("/api/imports/budgets/", {"file": file}, format="multipart")
        assert response.status_code == 400

    def test_rejects_file_with_no_data_rows(self):
        user = UserFactory()
        client = authed_client(user)

        file = xlsx_file([])
        response = client.post("/api/imports/budgets/", {"file": file}, format="multipart")
        assert response.status_code == 400

    def test_unknown_category_fails_that_row_only(self):
        user = UserFactory()
        client = authed_client(user)

        file = xlsx_file([("NotACategory", MONTH_STR, 15000, ""), ("Food", MONTH_STR, 5000, "")])
        response = client.post("/api/imports/budgets/", {"file": file}, format="multipart")

        batch = BudgetImportBatch.objects.get(id=response.data["id"])
        rows = list(batch.rows.order_by("row_number"))
        assert rows[0].status == BudgetImportRow.Status.FAILED
        assert "not found" in rows[0].error
        assert rows[1].status == BudgetImportRow.Status.PENDING

    def test_unparseable_month_fails(self):
        user = UserFactory()
        client = authed_client(user)

        file = xlsx_file([("Food", "not-a-month", 15000, "")])
        response = client.post("/api/imports/budgets/", {"file": file}, format="multipart")
        row = BudgetImportBatch.objects.get(id=response.data["id"]).rows.get()
        assert row.status == BudgetImportRow.Status.FAILED

    def test_non_positive_amount_fails(self):
        user = UserFactory()
        client = authed_client(user)

        file = xlsx_file([("Food", MONTH_STR, -100, "")])
        response = client.post("/api/imports/budgets/", {"file": file}, format="multipart")
        row = BudgetImportBatch.objects.get(id=response.data["id"]).rows.get()
        assert row.status == BudgetImportRow.Status.FAILED

    def test_household_not_a_member_of_fails(self):
        user = UserFactory()
        household = HouseholdFactory()  # user is not a member
        client = authed_client(user)

        file = xlsx_file([("Food", MONTH_STR, 15000, household.name)])
        response = client.post("/api/imports/budgets/", {"file": file}, format="multipart")
        row = BudgetImportBatch.objects.get(id=response.data["id"]).rows.get()
        assert row.status == BudgetImportRow.Status.FAILED
        assert "not found" in row.error or "member" in row.error

    def test_valid_household_stages_as_pending(self):
        user = UserFactory()
        household = HouseholdFactory()
        HouseholdMembershipFactory(user=user, household=household)
        client = authed_client(user)

        file = xlsx_file([("Food", MONTH_STR, 15000, household.name)])
        response = client.post("/api/imports/budgets/", {"file": file}, format="multipart")
        row = BudgetImportBatch.objects.get(id=response.data["id"]).rows.get()
        assert row.status == BudgetImportRow.Status.PENDING


@pytest.mark.django_db
class TestConfirm:
    def test_confirm_creates_budget(self):
        user = UserFactory()
        client = authed_client(user)
        file = xlsx_file([("Food", MONTH_STR, 15000, "")])
        batch_id = client.post("/api/imports/budgets/", {"file": file}, format="multipart").data["id"]

        response = client.post(f"/api/imports/budgets/{batch_id}/confirm/", {}, format="json")
        assert response.status_code == 200
        assert response.data["imported_count"] == 1

        budget = Budget.objects.get(user=user, household__isnull=True)
        assert budget.amount == 15000
        row = BudgetImportBatch.objects.get(id=batch_id).rows.get()
        assert row.status == BudgetImportRow.Status.IMPORTED
        assert row.budget_id == budget.id

    def test_confirm_updates_existing_budget(self):
        user = UserFactory()
        category = Category.objects.filter(is_system=True, name="Food").first()
        existing = BudgetFactory(user=user, category=category, month=THIS_MONTH, amount="10000.00")
        client = authed_client(user)

        file = xlsx_file([("Food", MONTH_STR, 20000, "")])
        batch_id = client.post("/api/imports/budgets/", {"file": file}, format="multipart").data["id"]
        client.post(f"/api/imports/budgets/{batch_id}/confirm/", {}, format="json")

        existing.refresh_from_db()
        assert existing.amount == 20000
        assert Budget.objects.filter(user=user, category=category, month=THIS_MONTH).count() == 1

    def test_cannot_confirm_twice(self):
        user = UserFactory()
        client = authed_client(user)
        file = xlsx_file([("Food", MONTH_STR, 15000, "")])
        batch_id = client.post("/api/imports/budgets/", {"file": file}, format="multipart").data["id"]

        client.post(f"/api/imports/budgets/{batch_id}/confirm/", {}, format="json")
        response = client.post(f"/api/imports/budgets/{batch_id}/confirm/", {}, format="json")
        assert response.status_code == 400

    def test_row_ids_can_exclude_rows(self):
        user = UserFactory()
        client = authed_client(user)
        file = xlsx_file([("Food", MONTH_STR, 15000, ""), ("Housing", MONTH_STR, 8000, "")])
        batch_id = client.post("/api/imports/budgets/", {"file": file}, format="multipart").data["id"]

        batch = BudgetImportBatch.objects.get(id=batch_id)
        food_row = batch.rows.get(raw_data__category="Food")
        response = client.post(
            f"/api/imports/budgets/{batch_id}/confirm/", {"row_ids": [str(food_row.id)]}, format="json"
        )
        assert response.data["imported_count"] == 1
        housing_row = batch.rows.get(raw_data__category="Housing")
        housing_row.refresh_from_db()
        assert housing_row.status == BudgetImportRow.Status.SKIPPED


@pytest.mark.django_db
class TestPreviewAndPermissions:
    def test_preview_lists_rows(self):
        user = UserFactory()
        client = authed_client(user)
        file = xlsx_file([("Food", MONTH_STR, 15000, "")])
        batch_id = client.post("/api/imports/budgets/", {"file": file}, format="multipart").data["id"]

        response = client.get(f"/api/imports/budgets/{batch_id}/preview/")
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_cannot_access_another_users_batch(self):
        owner = UserFactory()
        other = UserFactory()
        owner_client = authed_client(owner)
        file = xlsx_file([("Food", MONTH_STR, 15000, "")])
        batch_id = owner_client.post("/api/imports/budgets/", {"file": file}, format="multipart").data["id"]

        other_client = authed_client(other)
        response = other_client.get(f"/api/imports/budgets/{batch_id}/preview/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestTemplate:
    def test_template_download_has_expected_headers(self):
        user = UserFactory()
        client = authed_client(user)

        response = client.get("/api/imports/budgets/template/")
        assert response.status_code == 200
        workbook = openpyxl.load_workbook(io.BytesIO(response.content))
        header = [cell.value for cell in workbook.active[1]]
        assert header == ["Category", "Month", "Amount", "Household"]
