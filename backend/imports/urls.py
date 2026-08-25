from rest_framework.routers import DefaultRouter

from .views import BudgetImportBatchViewSet, ImportBatchViewSet

router = DefaultRouter()
router.register("budgets", BudgetImportBatchViewSet, basename="budget-import-batch")
router.register("", ImportBatchViewSet, basename="import-batch")

urlpatterns = router.urls
