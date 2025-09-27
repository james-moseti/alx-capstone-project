from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
)


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit objects.
    
    Permissions:
    - Read permissions (GET, HEAD, OPTIONS): Allowed for any request
    - Write permissions (POST, PUT, PATCH, DELETE): Only for admin/staff users
    """
    def has_permission(self, request, view):
        """
        Return True if permission is granted, False otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


@extend_schema_view(
    list=extend_schema(
        summary="List all categories",
        description="Retrieve a list of all active categories available in the system.",
        tags=["Categories"],
        responses={
            200: CategorySerializer(many=True),
            401: OpenApiResponse(description="Authentication credentials were not provided")
        }
    ),
    create=extend_schema(
        summary="Create a new category",
        description="Create a new product category. Requires admin permissions.",
        tags=["Categories"],
        responses={
            201: CategorySerializer,
            400: OpenApiResponse(description="Bad Request - Invalid data provided"),
            401: OpenApiResponse(description="Authentication credentials were not provided"),
            403: OpenApiResponse(description="Permission denied - Admin access required")
        }
    ),
    retrieve=extend_schema(
        summary="Get category details",
        description="Retrieve detailed information about a specific category.",
        tags=["Categories"],
        responses={
            200: CategorySerializer,
            404: OpenApiResponse(description="Category not found")
        }
    ),
    update=extend_schema(
        summary="Update category",
        description="Update a category completely. All fields are required. Requires admin permissions.",
        tags=["Categories"],
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(description="Bad Request - Invalid data provided"),
            401: OpenApiResponse(description="Authentication credentials were not provided"),
            403: OpenApiResponse(description="Permission denied - Admin access required"),
            404: OpenApiResponse(description="Category not found")
        }
    ),
    partial_update=extend_schema(
        summary="Partially update category",
        description="Update specific fields of a category. Only provided fields will be updated. Requires admin permissions.",
        tags=["Categories"],
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(description="Bad Request - Invalid data provided"),
            401: OpenApiResponse(description="Authentication credentials were not provided"),
            403: OpenApiResponse(description="Permission denied - Admin access required"),
            404: OpenApiResponse(description="Category not found")
        }
    ),
    destroy=extend_schema(
        summary="Delete category",
        description="Delete a category from the system. Requires admin permissions.",
        tags=["Categories"],
        responses={
            204: OpenApiResponse(description="Category deleted successfully"),
            401: OpenApiResponse(description="Authentication credentials were not provided"),
            403: OpenApiResponse(description="Permission denied - Admin access required"),
            404: OpenApiResponse(description="Category not found")
        }
    )
)
class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product categories.
    
    This viewset provides CRUD operations for categories:
    - List all active categories
    - Create new categories (admin only)
    - Retrieve specific category details
    - Update categories (admin only)
    - Delete categories (admin only)
    
    ## Permissions
    - **Read operations**: Available to all users
    - **Write operations**: Restricted to admin/staff users only
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


@extend_schema_view(
    list=extend_schema(
        summary="List products",
        description="""
        Retrieve a list of active products with comprehensive filtering, searching, and sorting options.
        
        ## Filtering Options
        - **category**: Filter by category ID (e.g., `?category=1`)
        - **is_active**: Filter by active status (e.g., `?is_active=true`)
        - **price**: Filter by exact price (e.g., `?price=99.99`)
        
        ## Search Functionality
        - **search**: Search across product name and description (e.g., `?search=laptop`)
        
        ## Sorting Options
        - **ordering**: Sort by `price`, `created_at`, or `updated_at`
        - Use minus sign (-) for descending order (e.g., `?ordering=-price`)
        - Multiple fields supported (e.g., `?ordering=-price,created_at`)
        
        ## Usage Examples
        - Get expensive electronics: `/products/?category=1&ordering=-price`
        - Search active smartphones: `/products/?search=smartphone&is_active=true`
        - Latest products first: `/products/?ordering=-created_at`
        """,
        tags=["Products"],
        parameters=[
            OpenApiParameter(
                name='category',
                description='Filter products by category ID',
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name='is_active',
                description='Filter by active status',
                required=False,
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name='price',
                description='Filter by exact price',
                required=False,
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name='search',
                description='Search in product name and description',
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name='ordering',
                description='Order by: price, created_at, updated_at (prefix with - for descending)',
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=['price', '-price', 'created_at', '-created_at', 'updated_at', '-updated_at']
            ),
        ],
        responses={
            200: ProductListSerializer(many=True),
            400: OpenApiResponse(description="Bad Request - Invalid query parameters")
        }
    ),
    create=extend_schema(
        summary="Create a new product",
        description="Create a new product in the system. Requires admin permissions.",
        tags=["Products"],
        request=ProductDetailSerializer,
        responses={
            201: ProductDetailSerializer,
            400: OpenApiResponse(description="Bad Request - Invalid data provided"),
            401: OpenApiResponse(description="Authentication credentials were not provided"),
            403: OpenApiResponse(description="Permission denied - Admin access required")
        }
    ),
    retrieve=extend_schema(
        summary="Get product details",
        description="Retrieve comprehensive information about a specific product including all details.",
        tags=["Products"],
        responses={
            200: ProductDetailSerializer,
            404: OpenApiResponse(description="Product not found")
        }
    ),
    update=extend_schema(
        summary="Update product",
        description="Update a product completely. All fields are required. Requires admin permissions.",
        tags=["Products"],
        request=ProductDetailSerializer,
        responses={
            200: ProductDetailSerializer,
            400: OpenApiResponse(description="Bad Request - Invalid data provided"),
            401: OpenApiResponse(description="Authentication credentials were not provided"),
            403: OpenApiResponse(description="Permission denied - Admin access required"),
            404: OpenApiResponse(description="Product not found")
        }
    ),
    partial_update=extend_schema(
        summary="Partially update product",
        description="Update specific fields of a product. Only provided fields will be updated. Requires admin permissions.",
        tags=["Products"],
        request=ProductDetailSerializer,
        responses={
            200: ProductDetailSerializer,
            400: OpenApiResponse(description="Bad Request - Invalid data provided"),
            401: OpenApiResponse(description="Authentication credentials were not provided"),
            403: OpenApiResponse(description="Permission denied - Admin access required"),
            404: OpenApiResponse(description="Product not found")
        }
    ),
    destroy=extend_schema(
        summary="Delete product",
        description="Remove a product from the system. This typically sets is_active to False rather than hard deletion. Requires admin permissions.",
        tags=["Products"],
        responses={
            204: OpenApiResponse(description="Product deleted successfully"),
            401: OpenApiResponse(description="Authentication credentials were not provided"),
            403: OpenApiResponse(description="Permission denied - Admin access required"),
            404: OpenApiResponse(description="Product not found")
        }
    )
)
class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products with advanced filtering, searching, and sorting capabilities.
    
    This viewset provides comprehensive CRUD operations for products with the following features:
    
    ## Core Operations
    - **List**: Get paginated list of products with filtering and search
    - **Create**: Add new products (admin only)
    - **Retrieve**: Get detailed product information
    - **Update**: Modify existing products (admin only) 
    - **Delete**: Remove products (admin only)
    
    ## Advanced Features
    - **Filtering**: By category, active status, and price
    - **Full-text search**: Across product names and descriptions
    - **Flexible sorting**: By price, creation date, or modification date
    - **Dual serializers**: Lightweight for lists, detailed for individual items
    
    ## Permissions
    - **Read operations**: Available to all users
    - **Write operations**: Restricted to admin/staff users only
    """
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
        """
        Return the appropriate serializer class based on the action.
        
        Returns:
        - ProductDetailSerializer: For single item views and write operations (more fields)
        - ProductListSerializer: For list views (optimized for performance)
        """
        if self.action in ["retrieve", "create", "update", "partial_update"]:
            return ProductDetailSerializer
        return ProductListSerializer

    @extend_schema(
        summary="Get products by category",
        description="""
        Retrieve all products within a specific category with the same filtering and search capabilities as the main product list.
        
        This endpoint supports all the same query parameters as the main product list:
        - search: Full-text search in name and description
        - ordering: Sort by price, created_at, or updated_at
        - Standard pagination applies
        """,
        tags=["Products"],
        parameters=[
            OpenApiParameter(
                name='category_id',
                description='ID of the category to filter products by',
                required=True,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name='search',
                description='Search in product name and description',
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name='ordering',
                description='Order by: price, created_at, updated_at (prefix with - for descending)',
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=['price', '-price', 'created_at', '-created_at', 'updated_at', '-updated_at']
            ),
        ],
        responses={
            200: ProductListSerializer(many=True),
            404: OpenApiResponse(description="Category not found")
        }
    )
    @action(detail=False, methods=['get'], url_path='by-category/(?P<category_id>[^/.]+)')
    def by_category(self, request, category_id=None):
        """
        Get all products in a specific category.
        
        This action provides category-specific product listing while maintaining
        all the search and filtering capabilities of the main product endpoint.
        """
        try:
            category = Category.objects.get(id=category_id, is_active=True)
            queryset = self.filter_queryset(self.queryset.filter(category=category))
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Category.DoesNotExist:
            return Response(
                {"detail": "Category not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        summary="Get featured products",
        description="Retrieve a list of featured products (assuming you have a featured field in your model)",
        tags=["Products"],
        responses={200: ProductListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products."""
        # Assuming you have a 'featured' field in your Product model
        # queryset = self.queryset.filter(featured=True)
        queryset = self.queryset.order_by('-created_at')[:10]  # Latest 10 as example
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)