from rest_framework import viewsets, permissions, mixins, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, extend_schema_view
from .models import Payment
from .serializers import PaymentSerializer
from orders.models import Order

# TODO FIX [CustomerPaymentViewSet]: could not derive type of path parameter "id" because it is untyped and obtaining queryset from the viewset failed. Consider adding a type to the path (e.g. <int:id>) or annotating the parameter type with @extend_schema. Defaulting to "string".

class IsOwner(permissions.BasePermission):
    """Customer can only see their own payments."""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


# --- Customer ViewSet ---
@extend_schema_view(
    list=extend_schema(
        summary="List customer payments",
        description=(
            "Retrieves a paginated list of all payments belonging to the authenticated customer. "
            "Payments are automatically filtered to show only those associated with the current user's orders. "
            "Results are ordered by creation date (newest first)."
        ),
        responses={
            200: OpenApiResponse(
                response=PaymentSerializer(many=True),
                description="List of customer's payments with pagination metadata"
            ),
            401: OpenApiResponse(
                description="Unauthorized. JWT token is missing, invalid, or expired."
            ),
        }
    ),
    retrieve=extend_schema(
        summary="Retrieve specific customer payment",
        description=(
            "Retrieves detailed information about a specific payment. "
            "Customers can only access their own payments - attempting to access "
            "another user's payment will result in a 404 error."
        ),
        responses={
            200: OpenApiResponse(
                response=PaymentSerializer,
                description="Payment details including status, amount, and associated order information"
            ),
            401: OpenApiResponse(
                description="Unauthorized. JWT token is missing, invalid, or expired."
            ),
            404: OpenApiResponse(
                description="Payment not found or does not belong to the authenticated user."
            ),
        }
    ),
    create=extend_schema(
        summary="Create a new payment",
        description=(
            "Creates a new payment record for an order. The payment amount and currency "
            "are automatically calculated from the associated order's grand_total and currency fields. "
            "The authenticated user is automatically set as the payment owner. "
            "Initial payment status is set to 'PENDING' and can be updated by admin users later."
        ),
        request=PaymentSerializer,
        responses={
            201: OpenApiResponse(
                response=PaymentSerializer,
                description="Payment created successfully with auto-calculated amount and currency"
            ),
            400: OpenApiResponse(
                description=(
                    "Validation error. Common issues include:\n"
                    "- Order ID is invalid or does not exist\n"
                    "- Order does not belong to the authenticated user\n"
                    "- Order already has a payment associated with it\n"
                    "- Required fields are missing"
                )
            ),
            401: OpenApiResponse(
                description="Unauthorized. JWT token is missing, invalid, or expired."
            ),
        },
        examples=[
            OpenApiExample(
                name="Create Payment",
                summary="Create a payment for an order",
                description="Creates a payment for order ID 123. Amount and currency are auto-calculated.",
                value={
                    "order": 123
                }
            )
        ]
    )
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
@extend_schema_view(
    list=extend_schema(
        summary="List all payments (Admin)",
        description=(
            "Retrieves a paginated list of all payments in the system. "
            "Only accessible by admin users. Includes payments from all customers "
            "with complete payment and order information. Results are ordered by creation date (newest first)."
        ),
        responses={
            200: OpenApiResponse(
                response=PaymentSerializer(many=True),
                description="List of all payments with pagination metadata"
            ),
            401: OpenApiResponse(
                description="Unauthorized. JWT token is missing, invalid, or expired."
            ),
            403: OpenApiResponse(
                description="Forbidden. User does not have admin privileges."
            ),
        }
    ),
    retrieve=extend_schema(
        summary="Retrieve specific payment (Admin)",
        description=(
            "Retrieves detailed information about any payment in the system. "
            "Only accessible by admin users. Includes complete payment details, "
            "associated order information, and customer data."
        ),
        responses={
            200: OpenApiResponse(
                response=PaymentSerializer,
                description="Complete payment details with order and customer information"
            ),
            401: OpenApiResponse(
                description="Unauthorized. JWT token is missing, invalid, or expired."
            ),
            403: OpenApiResponse(
                description="Forbidden. User does not have admin privileges."
            ),
            404: OpenApiResponse(
                description="Payment not found."
            ),
        }
    ),
    create=extend_schema(
        summary="Create payment (Admin)",
        description=(
            "Creates a new payment record as an admin user. "
            "Similar to customer payment creation but with admin privileges. "
            "The payment amount and currency are automatically calculated from the associated order. "
            "Useful for creating payments on behalf of customers or for manual payment processing."
        ),
        request=PaymentSerializer,
        responses={
            201: OpenApiResponse(
                response=PaymentSerializer,
                description="Payment created successfully"
            ),
            400: OpenApiResponse(
                description=(
                    "Validation error. Common issues include:\n"
                    "- Order ID is invalid or does not exist\n"
                    "- Order already has a payment associated with it\n"
                    "- Required fields are missing"
                )
            ),
            401: OpenApiResponse(
                description="Unauthorized. JWT token is missing, invalid, or expired."
            ),
            403: OpenApiResponse(
                description="Forbidden. User does not have admin privileges."
            ),
        }
    ),
    update=extend_schema(
        summary="Update payment status (Admin)",
        description=(
            "Updates the payment status for administrative purposes. "
            "This endpoint is specifically designed for payment status management and requires "
            "both order_id and status in the request body.\n\n"
            "**Payment Status Rules:**\n"
            "- `PAID`: Can be set at any time by admin to confirm customer payment\n"
            "- `REFUNDED`: Can only be set if the payment status is currently `PAID`\n\n"
            "**Important:** When a payment status is updated, the associated order status "
            "is automatically synchronized to maintain data consistency.\n\n"
            "**Use Cases:**\n"
            "- Mark payment as PAID after manual verification\n"
            "- Process refunds for previously paid orders\n"
            "- Correct payment statuses after external payment processing"
        ),
        request=PaymentSerializer,
        responses={
            200: OpenApiResponse(
                response=PaymentSerializer,
                description="Payment status updated successfully. Associated order status also updated."
            ),
            400: OpenApiResponse(
                description=(
                    "Bad request. Common issues include:\n"
                    "- Missing order_id or status in request body\n"
                    "- Invalid status value (must be 'PAID' or 'REFUNDED')\n"
                    "- Attempting to refund a payment that is not currently PAID\n"
                    "- Invalid order_id format"
                )
            ),
            401: OpenApiResponse(
                description="Unauthorized. JWT token is missing, invalid, or expired."
            ),
            403: OpenApiResponse(
                description="Forbidden. User does not have admin privileges."
            ),
            404: OpenApiResponse(
                description="Order or associated payment not found."
            ),
        },
        examples=[
            OpenApiExample(
                name="Mark Payment as Paid",
                summary="Confirm a customer payment",
                description="Marks a pending payment as PAID after verification",
                value={
                    "order_id": 15,
                    "status": "PAID"
                }
            ),
            OpenApiExample(
                name="Process Refund",
                summary="Refund a previously paid order",
                description="Changes status from PAID to REFUNDED for order 15",
                value={
                    "order_id": 15,
                    "status": "REFUNDED"
                }
            ),
        ]
    ),
    partial_update=extend_schema(
        summary="Partially update payment status (Admin)",
        description=(
            "Partially updates payment information. Same functionality as the full update endpoint "
            "but allows for partial data updates. Primarily used for status changes.\n\n"
            "Follows the same business rules as the full update endpoint."
        ),
        request=PaymentSerializer,
        responses={
            200: OpenApiResponse(
                response=PaymentSerializer,
                description="Payment partially updated successfully"
            ),
            400: OpenApiResponse(
                description="Validation error or business rule violation"
            ),
            401: OpenApiResponse(
                description="Unauthorized. JWT token is missing, invalid, or expired."
            ),
            403: OpenApiResponse(
                description="Forbidden. User does not have admin privileges."
            ),
            404: OpenApiResponse(
                description="Order or payment not found."
            ),
        }
    )
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