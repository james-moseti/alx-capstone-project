from rest_framework import generics, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
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
    summary="Register a new user account",
    description=(
        "Creates a new user account in the system. This endpoint is publicly accessible "
        "and does not require authentication. Upon successful registration, the user "
        "will be able to authenticate using their credentials."
    ),
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(
            response=RegisterSerializer,
            description="User account created successfully. Returns the user data."
        ),
        400: OpenApiResponse(
            description=(
                "Validation error. Common issues include:\n"
                "- Email already exists\n"
                "- Username already taken\n"
                "- Password doesn't meet requirements\n"
                "- Required fields are missing"
            )
        ),
    },
    tags=["Authentication"]
)
class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


# --- Me View (CRUD for current user with soft delete) ---
@extend_schema(
    summary="Retrieve current user profile",
    description=(
        "Returns the profile information of the currently authenticated user. "
        "Requires a valid JWT token in the Authorization header."
    ),
    responses={
        200: OpenApiResponse(
            response=UserSerializer, 
            description="Current user profile data"
        ),
        401: OpenApiResponse(
            description="Unauthorized. JWT token is missing, invalid, or expired."
        ),
    },
    tags=["User Management"]
)
class MeViewGet(generics.RetrieveAPIView):
    pass

@extend_schema(
    summary="Update current user profile",
    description=(
        "Updates the profile information of the currently authenticated user. "
        "Only the fields provided in the request will be updated. "
        "Requires a valid JWT token in the Authorization header."
    ),
    request=UserSerializer,
    responses={
        200: OpenApiResponse(
            response=UserSerializer,
            description="User profile updated successfully"
        ),
        400: OpenApiResponse(
            description=(
                "Validation error. Common issues include:\n"
                "- Email format is invalid\n"
                "- Email already exists for another user\n"
                "- Username already taken by another user\n"
                "- Required fields are invalid"
            )
        ),
        401: OpenApiResponse(
            description="Unauthorized. JWT token is missing, invalid, or expired."
        ),
    },
    tags=["User Management"]
)
class MeViewUpdate(generics.UpdateAPIView):
    pass

@extend_schema(
    summary="Deactivate current user account",
    description=(
        "Soft deletes the current user account by setting is_active=False. "
        "This preserves data integrity by maintaining user records for historical data "
        "(such as past orders) while preventing the user from logging in. "
        "The account cannot be reactivated through the API. "
        "Requires a valid JWT token in the Authorization header."
    ),
    responses={
        204: OpenApiResponse(
            description="User account deactivated successfully. No content returned."
        ),
        401: OpenApiResponse(
            description="Unauthorized. JWT token is missing, invalid, or expired."
        ),
    },
    tags=["User Management"]
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
    description=(
        "Allows the authenticated user to change their password. "
        "Requires the current password for verification and a new password. "
        "The user must be authenticated with a valid JWT token. "
        "After successful password change, existing JWT tokens remain valid "
        "until they expire naturally."
    ),
    request=ChangePasswordSerializer,
    responses={
        200: OpenApiResponse(
            description="Password changed successfully. Returns success message."
        ),
        400: OpenApiResponse(
            description=(
                "Validation error. Common issues include:\n"
                "- Current password is incorrect\n"
                "- New password doesn't meet security requirements\n"
                "- New password confirmation doesn't match\n"
                "- Required fields are missing"
            )
        ),
        401: OpenApiResponse(
            description="Unauthorized. JWT token is missing, invalid, or expired."
        ),
    },
    tags=["Authentication"]
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
    summary="Request password reset email",
    description=(
        "Initiates the password reset process by sending a reset link to the provided email address. "
        "If the email exists in the system, a password reset email will be sent containing "
        "a secure link with UID and token parameters. The link expires after a certain period. "
        "For security reasons, this endpoint always returns a success response regardless "
        "of whether the email exists in the system (to prevent email enumeration attacks). "
        "No authentication is required for this endpoint."
    ),
    request=PasswordResetRequestSerializer,
    responses={
        200: OpenApiResponse(
            description=(
                "Request processed successfully. If the email address is registered, "
                "a password reset link has been sent. Check your email inbox and spam folder."
            )
        ),
        400: OpenApiResponse(
            description=(
                "Validation error. Common issues include:\n"
                "- Email format is invalid\n"
                "- Email field is missing or empty"
            )
        ),
        500: OpenApiResponse(
            description="Server error. Email service may be temporarily unavailable."
        )
    },
    tags=["Authentication"]
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
    summary="Confirm password reset with token",
    description=(
        "Completes the password reset process using the UID and token received in the reset email. "
        "This endpoint validates the reset token and sets the new password for the user account. "
        "The UID and token are typically provided as URL parameters in the reset email link, "
        "but should be submitted in the request body along with the new password. "
        "Tokens have a limited lifespan and can only be used once. "
        "No authentication is required as the token serves as proof of identity."
    ),
    request=PasswordResetConfirmSerializer,
    responses={
        200: OpenApiResponse(
            description=(
                "Password reset completed successfully. The user can now log in "
                "with their new password. All existing sessions remain active."
            )
        ),
        400: OpenApiResponse(
            description=(
                "Bad request. Common issues include:\n"
                "- Invalid or malformed UID parameter\n"
                "- Invalid, expired, or already used token\n"
                "- New password doesn't meet security requirements\n"
                "- Required fields are missing\n"
                "- Reset link has been tampered with"
            )
        ),
    },
    tags=["Authentication"],
    parameters=[
        OpenApiParameter(
            name="uid",
            description="Base64-encoded user ID from the reset email link",
            required=False,
            type=str,
            location=OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            name="token",
            description="Password reset token from the reset email link",
            required=False,
            type=str,
            location=OpenApiParameter.QUERY
        ),
    ]
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
    