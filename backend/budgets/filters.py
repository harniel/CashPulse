import datetime

import django_filters

from .models import Budget


class BudgetFilter(django_filters.FilterSet):
    # Accepts "2026-08" (year-month) or a full ISO date, normalized to
    # the 1st either way, matching how Budget.month is always stored.
    month = django_filters.CharFilter(method="filter_month")

    class Meta:
        model = Budget
        fields = ["category", "household", "month"]

    def filter_month(self, queryset, name, value):
        try:
            if len(value) == 7:
                year, month = value.split("-")
                parsed = datetime.date(int(year), int(month), 1)
            else:
                parsed = datetime.date.fromisoformat(value).replace(day=1)
        except (ValueError, TypeError):
            return queryset.none()
        return queryset.filter(month=parsed)
