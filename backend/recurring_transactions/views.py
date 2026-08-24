from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response

from common.viewsets import HouseholdScopedModelViewSet

from . import services
from .models import RecurringTransaction
from .serializers import RecurringTransactionSerializer


class RecurringTransactionViewSet(HouseholdScopedModelViewSet):
    serializer_class = RecurringTransactionSerializer
    queryset = RecurringTransaction.objects.select_related(
        "account", "to_account", "category", "household"
    )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["account", "category", "type", "household", "frequency"]

    def perform_create(self, serializer):
        recurring = services.create_recurring(user=self.request.user, **serializer.validated_data)
        serializer.instance = recurring

    def perform_update(self, serializer):
        recurring = services.update_recurring(serializer.instance, **serializer.validated_data)
        serializer.instance = recurring

    @action(detail=True, methods=["post"], url_path="skip-next")
    def skip_next(self, request, pk=None):
        recurring = services.skip_next(self.get_object())
        return Response(self.get_serializer(recurring).data)
