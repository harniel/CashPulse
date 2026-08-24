from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.viewsets import OwnedModelViewSet

from . import services
from .models import Loan
from .serializers import LoanPaymentSerializer, LoanSerializer


class LoanViewSet(OwnedModelViewSet):
    serializer_class = LoanSerializer
    queryset = Loan.objects.all()

    def perform_create(self, serializer):
        loan = services.create_loan(user=self.request.user, **serializer.validated_data)
        serializer.instance = loan

    def perform_update(self, serializer):
        loan = services.update_loan(serializer.instance, **serializer.validated_data)
        serializer.instance = loan

    @action(detail=True, methods=["get"], url_path="amortization-schedule")
    def amortization_schedule(self, request, pk=None):
        loan = self.get_object()
        return Response(services.amortization_schedule(loan))

    @action(detail=True, methods=["get", "post"], url_path="payments")
    def payments(self, request, pk=None):
        loan = self.get_object()
        if request.method == "GET":
            return Response(LoanPaymentSerializer(loan.payments.all(), many=True).data)

        serializer = LoanPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = services.log_payment(
            loan,
            date_=serializer.validated_data["date"],
            amount=serializer.validated_data["amount"],
            is_extra=serializer.validated_data.get("is_extra", False),
        )
        return Response(LoanPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
