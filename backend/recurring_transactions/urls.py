from rest_framework.routers import DefaultRouter

from .views import RecurringTransactionViewSet

router = DefaultRouter()
router.register("", RecurringTransactionViewSet, basename="recurring-transaction")

urlpatterns = router.urls
