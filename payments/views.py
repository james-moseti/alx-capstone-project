from rest_framework import viewsets, permissions, mixins, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .models import Payment
from .serializers import PaymentSerializer
from orders.models import Order


class IsOwner(permissions.BasePermission):
    """Customer can only see their own payments."""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


# --- Customer ViewSet ---
@extend_schema(
    tags=["Payments"],
    summary="Customer payments",
    description="Customers can list, view, and create their own payments.",
    responses={
        200: OpenApiResponse(response=PaymentSerializer, description="Payment details"),
        201: OpenApiResponse(response=PaymentSerializer, description="Payment created"),
    },
)
class CustomerPaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        order = serializer.validated_data["order"]
        serializer.save(
            user=self.request.user,
            amount=order.grand_total,
            currency=order.currency
        )


# --- Admin ViewSet ---
@extend_schema(
    tags=["Admin Payments"],
    summary="Admin payments",
    description=(
        "Admins can **list**, **view**, and **create** payments. "
        "They can also use **PUT** to update payment status (PAID or REFUNDED). "
        "- `PAID` means customer payment is confirmed. \n"
        "- `REFUNDED` is only allowed if the payment was already `PAID`."
    ),
    examples=[
        OpenApiExample(
            "Mark payment as PAID",
            summary="Confirm a payment",
            request_only=True,
            value={"order_id": 15, "status": "PAID"},
        ),
        OpenApiExample(
            "Mark payment as REFUNDED",
            summary="Refund a previously paid order",
            request_only=True,
            value={"order_id": 15, "status": "REFUNDED"},
        ),
    ],
    responses={
        200: OpenApiResponse(response=PaymentSerializer, description="Payment updated"),
        400: OpenApiResponse(description="Invalid request"),
        403: OpenApiResponse(description="Forbidden"),
    },
)
class AdminPaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Payment.objects.all()

    def update(self, request, *args, **kwargs):
        """
        Admin updates a payment by providing:
        {
            "order_id": <int>,
            "status": "PAID" | "REFUNDED"
        }

        Rules:
        - "PAID" can be set anytime by admin.
        - "REFUNDED" is only valid if the payment was already PAID.
        """
        order_id = request.data.get("order_id")
        status_value = request.data.get("status")

        if not order_id or not status_value:
            return Response(
                {"detail": "order_id and status are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = Order.objects.get(id=order_id)
            payment = order.payment
        except (Order.DoesNotExist, Payment.DoesNotExist):
            return Response(
                {"detail": "Order or payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only allow PAID or REFUNDED
        if status_value not in ["PAID", "REFUNDED"]:
            return Response(
                {"detail": "Status must be either 'PAID' or 'REFUNDED'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Refunds require payment to have been paid
        if status_value == "REFUNDED" and payment.status != "PAID":
            return Response(
                {"detail": "Cannot refund a payment that is not already PAID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update payment + order
        payment.status = status_value
        payment.save(update_fields=["status", "updated_at"])

        order.status = status_value
        order.save(update_fields=["status", "updated_at"])

        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)