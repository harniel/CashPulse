from django_filters.rest_framework import DjangoFilterBackend

from common.viewsets import HouseholdScopedModelViewSet

from . import services
from .filters import TransactionFilter
from .models import Transaction
from .serializers import TransactionSerializer


class TransactionViewSet(HouseholdScopedModelViewSet):
    """
    Visible to the transaction's own user OR, when it's shared
    (household is set), any member of that household — who can then also
    edit/delete it, per the "if shared, any member's" user story (§6).
    Reaching the object at all already proves membership, so no extra
    role gate is layered on top the way Households' admin actions are.
    """

    serializer_class = TransactionSerializer
    queryset = Transaction.objects.select_related("account", "to_account", "category", "household")
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter

    def perform_create(self, serializer):
        transaction = services.create_transaction(
            user=self.request.user, **serializer.validated_data
        )
        serializer.instance = transaction

    def perform_update(self, serializer):
        transaction = services.update_transaction(
            serializer.instance, actor=self.request.user, **serializer.validated_data
        )
        serializer.instance = transaction

    def perform_destroy(self, instance):
        services.delete_transaction(instance, actor=self.request.user)
