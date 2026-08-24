from django.urls import path

from .views import ForecastView

urlpatterns = [
    path("", ForecastView.as_view(), name="forecast"),
]
