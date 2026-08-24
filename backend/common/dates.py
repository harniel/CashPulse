import calendar
from datetime import timedelta


def add_months(from_date, months):
    """Add whole months, clamping the day if the target month is shorter
    (Jan 31 + 1 month -> Feb 28/29, not Mar 3 or an OverflowError)."""
    total = from_date.month - 1 + months
    year = from_date.year + total // 12
    month = total % 12 + 1
    day = min(from_date.day, calendar.monthrange(year, month)[1])
    return from_date.replace(year=year, month=month, day=day)


def advance_date(from_date, frequency):
    """
    Advance a date by one occurrence of a named frequency — shared by
    recurring_transactions (advancing next_run_date) and forecasting
    (simulating recurring transactions forward). `frequency` is a plain
    string ("weekly"/"biweekly"/"monthly"/"yearly") rather than an enum
    import, so this stays free of any app dependency.
    """
    if frequency == "weekly":
        return from_date + timedelta(days=7)
    if frequency == "biweekly":
        return from_date + timedelta(days=14)
    if frequency == "monthly":
        return add_months(from_date, 1)
    if frequency == "yearly":
        return add_months(from_date, 12)
    raise ValueError(f"Unknown frequency: {frequency}")
