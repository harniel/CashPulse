from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/categories/", include("categories.urls")),
    path("api/households/", include("households.urls")),
    path("api/invitations/", include("households.invitation_urls")),
    path("api/transactions/", include("transactions.urls")),
    path("api/budgets/", include("budgets.urls")),
    path("api/dashboard/", include("dashboard.urls")),
    path("api/recurring-transactions/", include("recurring_transactions.urls")),
    path("api/loans/", include("loans.urls")),
    path("api/savings-goals/", include("savings.urls")),
    path("api/forecast/", include("forecasting.urls")),
    path("api/imports/", include("imports.urls")),
    path("api/notifications/", include("notifications.urls")),
]
