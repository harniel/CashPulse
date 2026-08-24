from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.viewsets import HouseholdScopedModelViewSet

from . import services
from .models import SavingsGoal
from .serializers import SavingsContributionSerializer, SavingsGoalSerializer


class SavingsGoalViewSet(HouseholdScopedModelViewSet):
    serializer_class = SavingsGoalSerializer
    queryset = SavingsGoal.objects.select_related("household")

    def perform_create(self, serializer):
        goal = services.create_goal(user=self.request.user, **serializer.validated_data)
        serializer.instance = goal

    def perform_update(self, serializer):
        goal = services.update_goal(serializer.instance, **serializer.validated_data)
        serializer.instance = goal

    @action(detail=True, methods=["get", "post"], url_path="contributions")
    def contributions(self, request, pk=None):
        goal = self.get_object()
        if request.method == "GET":
            return Response(SavingsContributionSerializer(goal.contributions.all(), many=True).data)

        serializer = SavingsContributionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contribution = services.log_contribution(
            goal,
            date_=serializer.validated_data["date"],
            amount=serializer.validated_data["amount"],
        )
        return Response(
            SavingsContributionSerializer(contribution).data, status=status.HTTP_201_CREATED
        )
