from django.urls import path
from .views import (
    RegisterView, MeView, ChangePasswordView,
    PasswordResetRequestView, PasswordResetConfirmView
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("me/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("reset-password/", PasswordResetRequestView.as_view(), name="reset-password"),
    path("reset-password-confirm/", PasswordResetConfirmView.as_view(), name="reset-password-confirm"),
]
