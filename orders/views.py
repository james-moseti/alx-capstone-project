from rest_framework import viewsets, permissions, filters, mixins
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer
from .permissions import IsOwnerOrAdmin

# TODO Fix the admin view of all products

# --- Customer Order API ---
@extend_schema(
    tags=["Orders"],
    summary="Create or manage your orders",
    description="Customers can create new orders, list their orders, or view details of one order. Requires JWT token.",
    responses={
        200: OpenApiResponse(response=OrderSerializer, description="Order details"),
        201: OpenApiResponse(response=OrderSerializer, description="Order created successfully"),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Unauthorized"),
    },
    examples=[
        OpenApiExample(
            "Create order example",
            request_only=True,
            value={
                "currency": "USD",
                "items": [
                    {"product_id": 1, "quantity": 2},
                    {"product_id": 3, "quantity": 1}
                ],
                "shipping_address": {
                    "full_name": "Alice W",
                    "line1": "123 Market St",
                    "city": "Nairobi",
                    "postal_code": "00100",
                    "country": "KE"
                },
                "billing_address": {
                    "full_name": "Alice W",
                    "line1": "123 Market St",
                    "city": "Nairobi",
                    "postal_code": "00100",
                    "country": "KE"
                }
            }
        )
    ],
)
class OrderViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    queryset = Order.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["created_at", "grand_total", "status"]
    ordering = ["-created_at"]
    filterset_fields = ["status", "currency"]
    search_fields = ["number", "payment_reference"]

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs


# --- Admin Orders API ---
@extend_schema(
    tags=["Admin Orders"],
    summary="Admin view of all orders",
    description="Admins can list or retrieve all orders with filters, search, and sorting.",
    responses={200: OpenApiResponse(response=OrderSerializer, description="Order details")},
)
class AdminOrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["status", "currency", "user"]
    search_fields = ["number", "payment_reference", "user__username", "user__email"]
    ordering_fields = ["created_at", "grand_total"]
    ordering = ["-created_at"]
