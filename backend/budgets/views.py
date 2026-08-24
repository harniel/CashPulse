from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response

from common.viewsets import HouseholdScopedModelViewSet

from . import services
from .filters import BudgetFilter
from .models import Budget
from .serializers import BudgetSerializer


class BudgetViewSet(HouseholdScopedModelViewSet):
    serializer_class = BudgetSerializer
    queryset = Budget.objects.select_related("category", "household")
    filter_backends = [DjangoFilterBackend]
    filterset_class = BudgetFilter

    def perform_create(self, serializer):
        budget = services.create_budget(user=self.request.user, **serializer.validated_data)
        serializer.instance = budget

    def perform_update(self, serializer):
        budget = services.update_budget(
            serializer.instance, actor=self.request.user, **serializer.validated_data
        )
        serializer.instance = budget

    def perform_destroy(self, instance):
        services.delete_budget(instance, actor=self.request.user)

    @action(detail=True, methods=["get"])
    def performance(self, request, pk=None):
        budget = self.get_object()
        history = services.budget_history(budget)
        serializer = self.get_serializer(history, many=True)
        return Response(serializer.data)
