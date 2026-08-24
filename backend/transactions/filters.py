import django_filters

from .models import Transaction


class TransactionFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    is_shared = django_filters.BooleanFilter(method="filter_is_shared")

    class Meta:
        model = Transaction
        fields = ["account", "category", "type", "household", "date_from", "date_to", "is_shared"]

    def filter_is_shared(self, queryset, name, value):
        return queryset.filter(household__isnull=not value)
