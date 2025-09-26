from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
)


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission:
    - SAFE methods (GET, HEAD, OPTIONS) → allowed for everyone
    - Write methods (POST, PUT, PATCH, DELETE) → only for staff/admin
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    permission_classes = [IsAdminOrReadOnly]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]

    # Filtering
    filterset_fields = ["category", "is_active", "price"]

    # Search fields
    search_fields = ["name", "description"]

    # Sorting
    ordering_fields = ["price", "created_at", "updated_at"]
    ordering = ["-created_at"]  # default

    def get_serializer_class(self):
        # Use detailed serializer for single product view and writes
        if self.action in ["retrieve", "create", "update", "partial_update"]:
            return ProductDetailSerializer
        # Use lightweight serializer for lists
        return ProductListSerializer
