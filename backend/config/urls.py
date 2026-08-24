from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/categories/", include("categories.urls")),
    path("api/households/", include("households.urls")),
    path("api/invitations/", include("households.invitation_urls")),
]
