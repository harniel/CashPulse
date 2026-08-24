from django.db.models import Q
from rest_framework import viewsets


class OwnedModelViewSet(viewsets.ModelViewSet):
    """
    Base for every viewset over user-owned financial data.

    This is the single choke point for the rule from the blueprint
    (Section 10/20): a user must never be able to read, edit, or delete
    another user's record, even by guessing an ID. Rather than repeating
    `.filter(user=request.user)` in every app's view and hoping nobody
    forgets it on the next one, every resource viewset inherits from
    here and only needs to set `owner_field` (default 'user').

    get_object() relies on DRF calling get_queryset() first, so scoping
    the queryset alone is enough to turn "not yours" into a 404 rather
    than a 403 — we don't want to even confirm the record exists.
    """

    owner_field = "user"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**{self.owner_field: self.request.user})

    def perform_create(self, serializer):
        serializer.save(**{self.owner_field: self.request.user})


class HouseholdScopedModelViewSet(viewsets.ModelViewSet):
    """
    Extends OwnedModelViewSet's "your data or 404" rule (Section 9) to
    resources that can also be shared with a household: visible if you
    own it OR you're a member of the household it's shared with — an OR
    across two relations, mirroring how CategoryViewSet already ORs
    user-owned against system-shared.
    """

    owner_field = "user"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        return queryset.filter(
            Q(**{self.owner_field: user}) | Q(household__memberships__user=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(**{self.owner_field: self.request.user})
