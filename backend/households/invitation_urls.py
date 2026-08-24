from django.urls import path

from .views import InvitationAcceptView, InvitationDeclineView

urlpatterns = [
    path("<str:token>/accept/", InvitationAcceptView.as_view(), name="invitation-accept"),
    path("<str:token>/decline/", InvitationDeclineView.as_view(), name="invitation-decline"),
]
