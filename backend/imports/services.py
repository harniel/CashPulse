"""
CSV import pipeline (Section 16): upload+validate happen together in
create_batch() (no pandas — stdlib csv is plenty at this scale), then
confirm_batch() persists whichever rows the user approved. Duplicate
detection flags, never auto-skips — the user decides per row.
"""

import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction as db_transaction
from rest_framework.exceptions import ValidationError

from categories.models import Category
from transactions.models import Transaction

from .models import ImportBatch, ImportRow

MAX_ROWS = 500
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
DUPLICATE_WINDOW_DAYS = 2
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]


def _parse_date(raw_value):
    raw_value = (raw_value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw_value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(raw_value):
    raw_value = (raw_value or "").strip().replace(",", "")
    try:
        amount = Decimal(raw_value)
    except InvalidOperation:
        return None
    if amount == 0:
        return None
    return amount


def _default_category(kind):
    # Bank CSV exports don't categorize — every imported row lands in the
    # matching system catch-all category (seeded by
    # categories/migrations/0002_seed_default_categories.py) and the user
    # recategorizes afterward through the normal Transaction PATCH endpoint,
    # same as any other transaction.
    name = "Other Income" if kind == Transaction.Type.INCOME else "Other Expense"
    return Category.objects.filter(is_system=True, kind=kind, name=name).first()


def _is_duplicate(account, row_date, amount):
    window_start = row_date - timedelta(days=DUPLICATE_WINDOW_DAYS)
    window_end = row_date + timedelta(days=DUPLICATE_WINDOW_DAYS)
    return Transaction.objects.filter(
        account=account, date__gte=window_start, date__lte=window_end, amount=amount
    ).exists()


def create_batch(user, account, uploaded_file, date_column, description_column, amount_column):
    if account.user_id != user.id:
        raise ValidationError({"account": "You don't have access to that account."})
    if not uploaded_file.name.lower().endswith(".csv"):
        raise ValidationError({"file": "Only .csv files are accepted."})
    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError({"file": f"File exceeds the {MAX_FILE_SIZE_BYTES // 1024}KB limit."})

    try:
        decoded = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError({"file": "Could not read the file as UTF-8 text."})

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise ValidationError({"file": "The file has no header row."})
    for column in (date_column, description_column, amount_column):
        if column not in reader.fieldnames:
            raise ValidationError({"file": f"Column '{column}' not found in the file header."})

    rows = list(reader)
    if not rows:
        raise ValidationError({"file": "The file has no data rows."})
    if len(rows) > MAX_ROWS:
        raise ValidationError(
            {"file": f"This file has {len(rows)} rows; the limit for a single import is {MAX_ROWS}."}
        )

    with db_transaction.atomic():
        batch = ImportBatch.objects.create(
            user=user,
            account=account,
            filename=uploaded_file.name,
            row_count=len(rows),
            date_column=date_column,
            description_column=description_column,
            amount_column=amount_column,
        )
        for raw_row in rows:
            _stage_row(batch, account, raw_row, date_column, amount_column)

    return batch


def _stage_row(batch, account, raw_row, date_column, amount_column):
    row_date = _parse_date(raw_row.get(date_column))
    amount = _parse_amount(raw_row.get(amount_column))

    if row_date is None:
        ImportRow.objects.create(
            batch=batch,
            raw_data=raw_row,
            status=ImportRow.Status.FAILED,
            error=f"Couldn't parse '{raw_row.get(date_column)}' as a date.",
        )
        return
    if amount is None:
        ImportRow.objects.create(
            batch=batch,
            raw_data=raw_row,
            status=ImportRow.Status.FAILED,
            error=f"Couldn't parse '{raw_row.get(amount_column)}' as a nonzero amount.",
        )
        return

    ImportRow.objects.create(
        batch=batch,
        raw_data=raw_row,
        status=ImportRow.Status.PENDING,
        is_duplicate=_is_duplicate(account, row_date, abs(amount)),
    )


def confirm_batch(batch, row_ids=None):
    """
    Persists a Transaction for each selected pending row. `row_ids=None`
    means "everything not flagged as a duplicate" — an explicit list lets
    the caller include specific duplicates or exclude specific rows.
    Whatever's left pending afterward is marked SKIPPED; the batch can
    only be confirmed once.
    """
    if batch.status == ImportBatch.Status.CONFIRMED:
        raise ValidationError("This import has already been confirmed.")

    pending_rows = list(batch.rows.filter(status=ImportRow.Status.PENDING))
    pending_ids = {row.id for row in pending_rows}

    if row_ids is None:
        selected_ids = {row.id for row in pending_rows if not row.is_duplicate}
    else:
        selected_ids = set(row_ids)
        unknown = selected_ids - pending_ids
        if unknown:
            raise ValidationError(
                {"row_ids": f"Unknown or non-pending row id(s): {sorted(str(i) for i in unknown)}"}
            )

    imported = []
    with db_transaction.atomic():
        for row in pending_rows:
            if row.id not in selected_ids:
                row.status = ImportRow.Status.SKIPPED
                row.save(update_fields=["status"])
                continue

            row_date = _parse_date(row.raw_data.get(batch.date_column))
            amount = _parse_amount(row.raw_data.get(batch.amount_column))
            description = (row.raw_data.get(batch.description_column) or "").strip()
            type_ = Transaction.Type.EXPENSE if amount < 0 else Transaction.Type.INCOME
            category = _default_category(type_)
            if category is None:
                raise ValidationError(
                    "No default category is configured for imported transactions."
                )

            imported_transaction = Transaction.objects.create(
                user=batch.user,
                account=batch.account,
                category=category,
                type=type_,
                amount=abs(amount),
                currency=batch.account.currency,
                date=row_date,
                description=description,
            )
            row.status = ImportRow.Status.IMPORTED
            row.transaction = imported_transaction
            row.save(update_fields=["status", "transaction"])
            imported.append(imported_transaction)

        batch.status = ImportBatch.Status.CONFIRMED
        batch.save(update_fields=["status"])

    return imported
