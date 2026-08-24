from django.utils import timezone
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, GenericViewSet
):
    """
    Read-only except for "mark read": every field is read_only on the
    serializer, and PATCH always sets read_at to now regardless of what
    body is sent — Section 10's "PATCH {id} (mark read)" is a fixed
    action, not general field editing. Notifications are only ever
    created by the sweep (Section 17), never via this API.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.instance.read_at = timezone.now()
        serializer.instance.save(update_fields=["read_at"])
