from django_filters.rest_framework import DjangoFilterBackend
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
