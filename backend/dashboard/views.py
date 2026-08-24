from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


class DashboardSummaryView(APIView):
    """
    Single GET, a small fixed set of aggregate queries (Section 25) — no
    per-widget endpoints. Scope defaults to personal; pass ?household=<id>
    to view a household's shared transactions/budgets instead (net worth
    stays personal either way — see services.net_worth_by_month).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        household = services.resolve_household(request.user, request.query_params.get("household"))
        return Response(services.summary(request.user, household))
