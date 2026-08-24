from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter

from common.viewsets import OwnedModelViewSet

from .models import Account
from .serializers import AccountSerializer


class AccountViewSet(OwnedModelViewSet):
    serializer_class = AccountSerializer
    queryset = Account.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["account_type", "is_active"]
    search_fields = ["name", "institution"]

    def perform_destroy(self, instance):
        # Transaction.account/to_account use on_delete=PROTECT so deleting
        # an account can never silently take transaction history with it —
        # deactivate (is_active=False) instead, or clear its transactions first.
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError(
                "This account has transactions and can't be deleted — deactivate it instead."
            )
