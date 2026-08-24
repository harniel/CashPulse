from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """
    DRF's default handler only special-cases Http404/PermissionDenied — a
    plain django.core.exceptions.ValidationError (e.g. from a model's
    save() calling full_clean(), which several apps here do as defense in
    depth alongside serializer-level checks) isn't a DRF APIException, so
    it falls through to an unhandled 500 instead of a clean 400. This
    converts it once, for every app, instead of each one needing to
    duplicate the conversion in its own serializer.
    """
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
        exc = DRFValidationError(detail)

    return drf_exception_handler(exc, context)
