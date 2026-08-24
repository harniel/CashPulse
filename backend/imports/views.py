from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from accounts.models import Account

from . import services
from .models import ImportBatch
from .serializers import ImportBatchSerializer, ImportRowSerializer


class ImportBatchViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    Not a plain ModelViewSet: creation takes a multipart file + a column
    mapping, not a JSON body shaped like ImportBatch's own fields, so
    `create()` is handled explicitly rather than through a writable
    serializer.
    """

    serializer_class = ImportBatchSerializer
    permission_classes = [IsAuthenticated]
    # MultiPart for the file upload (create); JSON for confirm's row_ids body.
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return ImportBatch.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            raise ValidationError({"file": "This field is required."})

        account_id = request.data.get("account")
        try:
            account = Account.objects.get(id=account_id, user=request.user)
        except (Account.DoesNotExist, ValueError, DjangoValidationError):
            raise ValidationError({"account": "Not a valid account."})

        column_fields = {}
        for field in ("date_column", "description_column", "amount_column"):
            value = request.data.get(field)
            if not value:
                raise ValidationError({field: "This field is required."})
            column_fields[field] = value

        batch = services.create_batch(
            user=request.user, account=account, uploaded_file=uploaded_file, **column_fields
        )
        return Response(ImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        batch = self.get_object()
        return Response(ImportRowSerializer(batch.rows.all(), many=True).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        batch = self.get_object()
        imported = services.confirm_batch(batch, row_ids=request.data.get("row_ids"))
        return Response(
            {"imported_count": len(imported), "batch": ImportBatchSerializer(batch).data}
        )
