from rest_framework import generics, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from .serializers import (
    RegisterSerializer, UserSerializer, ChangePasswordSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)

token_generator = PasswordResetTokenGenerator()


# --- Register View ---
@extend_schema(
    summary="Register a new user",
    description="Creates a new user account. No authentication required.",
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(
            response=RegisterSerializer,
            description="User created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
    }
)
class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


# --- Me View (CRUD for current user with soft delete) ---
@extend_schema(
    summary="Manage current authenticated user",
    description=(
        "Retrieve, update, or deactivate the currently authenticated user. "
        "DELETE will **soft delete** the user (sets is_active=False) so past orders remain intact."
    ),
    responses={
        200: OpenApiResponse(response=UserSerializer, description="User details"),
        204: OpenApiResponse(description="User deactivated successfully"),
        401: OpenApiResponse(description="Unauthorized — invalid or missing JWT token"),
    }
)
class MeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if not user.is_active:
            return Response(status=status.HTTP_204_NO_CONTENT)  # already inactive
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Change Password View ---
@extend_schema(
    summary="Change password for current user",
    description="Requires the current password and a new password. JWT authentication required.",
    request=ChangePasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password changed successfully"),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Unauthorized — invalid or missing JWT token"),
    }
)
class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['post']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Verify old password
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

        # Set new password
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)


# --- Request Reset Link ---
@extend_schema(
    summary="Request password reset",
    description=(
        "Send a reset link to the provided email. "
        "The email includes a UID and token for confirming the reset. "
        "Always returns success to avoid leaking registered emails."
    ),
    request=PasswordResetRequestSerializer,
    responses={
        200: OpenApiResponse(description="Reset link sent (if email exists)."),
    }
)
class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "If this email exists, a reset link has been sent."}, status=200)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)

        reset_link = f"{request.build_absolute_uri('/users/reset-password-confirm/')}?uid={uid}&token={token}"

        send_mail(
            subject="Password Reset",
            message=f"Click the link to reset your password: {reset_link}",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
            recipient_list=[email],
        )

        return Response({"detail": "If this email exists, a reset link has been sent."}, status=200)


# --- Confirm Reset ---
@extend_schema(
    summary="Confirm password reset",
    description="Confirm a password reset using UID and token from the reset email, and set a new password.",
    request=PasswordResetConfirmSerializer,
    responses={
        200: OpenApiResponse(description="Password reset successful"),
        400: OpenApiResponse(description="Invalid or expired token"),
    }
)
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Invalid link"}, status=400)

        if not token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired token"}, status=400)

        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password reset successful"}, status=200)
