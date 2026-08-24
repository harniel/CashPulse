from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import Category
from .serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Doesn't inherit OwnedModelViewSet: categories aren't purely
    user-owned, they're user-owned OR system-seeded-and-shared, which
    needs an OR in the queryset rather than a straight equality filter.
    Write operations are still locked to "yours only" — is_system rows
    are visible to everyone but mutable by no one via the API.
    """

    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["kind", "is_system", "parent"]

    def get_queryset(self):
        user = self.request.user
        return Category.objects.filter(Q(user=user) | Q(is_system=True))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_system=False)

    def perform_update(self, serializer):
        if serializer.instance.is_system:
            raise PermissionDenied("System categories can't be modified.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_system:
            raise PermissionDenied("System categories can't be deleted.")
        instance.delete()
