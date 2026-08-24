from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


class ForecastView(APIView):
    """
    GET /api/forecast/?household=<id>&trailing_months=6&projection_months=12
    Scope defaults to personal; trailing/projection windows default to
    Section 15's 6/12 but are explicit query params, not hidden constants,
    since the whole point is showing the assumptions behind the number.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        household = services.resolve_household(request.user, request.query_params.get("household"))
        trailing_months = self._positive_int(
            request.query_params.get("trailing_months"), services.DEFAULT_TRAILING_MONTHS, "trailing_months"
        )
        projection_months = self._positive_int(
            request.query_params.get("projection_months"),
            services.DEFAULT_PROJECTION_MONTHS,
            "projection_months",
        )
        return Response(
            services.project(
                request.user,
                household,
                trailing_months=trailing_months,
                projection_months=projection_months,
            )
        )

    @staticmethod
    def _positive_int(raw_value, default, field_name):
        if raw_value is None:
            return default
        try:
            value = int(raw_value)
        except ValueError:
            raise ValidationError({field_name: "Must be a whole number."})
        if value <= 0:
            raise ValidationError({field_name: "Must be greater than zero."})
        return value
