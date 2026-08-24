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
