from decimal import Decimal
from django.conf import settings
from django.db import models


class Address(models.Model):
    # Snapshot storage (don't reuse user profile fields that can change)
    full_name = models.CharField(max_length=255)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=2, default="US")  # ISO-3166-1 alpha-2
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        indexes = [
            # Geographic queries - city/state/country combinations
            models.Index(fields=['country', 'state', 'city'], name='address_location_idx'),
            models.Index(fields=['postal_code', 'country'], name='address_postal_idx'),
            
            # Name lookup for customer service
            models.Index(fields=['full_name'], name='address_name_idx'),
        ]

    def __str__(self):
        return f"{self.full_name}, {self.line1}, {self.city}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELED = "CANCELED", "Canceled"
        REFUNDED = "REFUNDED", "Refunded"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    number = models.CharField(max_length=50, unique=True)  # e.g. "ORD-2025-000123"
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    shipping_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name="shipping_orders")
    billing_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name="billing_orders")

    currency = models.CharField(max_length=3, default="USD")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    payment_reference = models.CharField(max_length=100, blank=True)  # e.g. provider charge id
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Most critical: user order history (primary customer query)
            models.Index(fields=['user', '-created_at'], name='order_user_created_idx'),
            
            # Status-based queries for admin/fulfillment
            models.Index(fields=['status', '-created_at'], name='order_status_created_idx'),
            
            # User + status combinations (user's pending orders, etc.)
            models.Index(fields=['user', 'status'], name='order_user_status_idx'),
            
            # Active orders by status (exclude canceled/refunded)
            models.Index(
                fields=['status', '-created_at'],
                condition=models.Q(is_active=True),
                name='order_active_status_idx'
            ),
            
            # Date range queries for reporting
            models.Index(fields=['created_at'], name='order_created_date_idx'),
            models.Index(fields=['-created_at'], name='order_created_desc_idx'),
            
            # Payment tracking
            models.Index(fields=['payment_reference'], name='order_payment_ref_idx'),
            
            # Financial reporting queries
            models.Index(fields=['currency', 'status', 'created_at'], name='order_currency_status_idx'),
            models.Index(fields=['grand_total'], name='order_total_idx'),
            
            # High-value orders (for analysis/fraud detection)
            models.Index(
                fields=['-grand_total', '-created_at'],
                condition=models.Q(grand_total__gte=Decimal('1000.00')),
                name='order_high_value_idx'
            ),
            
            # Shipping/fulfillment queries
            models.Index(fields=['shipping_address', 'status'], name='order_shipping_status_idx'),
            
            # Recent pending orders (common fulfillment query)
            models.Index(
                fields=['-created_at'],
                condition=models.Q(status__in=['PENDING', 'PAID'], is_active=True),
                name='order_pending_recent_idx'
            ),
        ]

    def __str__(self):
        return f"{self.number} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    name = models.CharField(max_length=255)  # snapshot
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        indexes = [
            # Most common: get all items for an order (automatic with FK)
            # Django creates this automatically, but being explicit:
            models.Index(fields=['order'], name='orderitem_order_idx'),
            
            # Product popularity/sales analysis
            models.Index(fields=['product', 'quantity'], name='orderitem_product_qty_idx'),
            
            # Revenue analysis by product
            models.Index(fields=['product', 'line_total'], name='orderitem_product_total_idx'),
            
            # Price point analysis
            models.Index(fields=['unit_price'], name='orderitem_unit_price_idx'),
            
            # High-quantity orders (bulk purchases)
            models.Index(
                fields=['product', '-quantity'],
                condition=models.Q(quantity__gte=5),
                name='orderitem_bulk_orders_idx'
            ),
            
            # High-value line items
            models.Index(
                fields=['-line_total'],
                condition=models.Q(line_total__gte=Decimal('500.00')),
                name='orderitem_high_value_idx'
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.name}"


# Custom migration for advanced PostgreSQL features
"""
Additional indexes you might add via migration for advanced analytics:

from django.db import migrations
from django.contrib.postgres.operations import BtreeGinExtension

class Migration(migrations.Migration):
    operations = [
        BtreeGinExtension(),
        
        # Multi-column GIN index for complex order queries
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY order_multi_gin_idx ON orders_order USING gin (user_id, status, currency);",
            reverse_sql="DROP INDEX IF EXISTS order_multi_gin_idx;"
        ),
        
        # Date partitioning preparation (for very large order volumes)
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY order_monthly_idx ON orders_order (date_trunc('month', created_at), status);",
            reverse_sql="DROP INDEX IF EXISTS order_monthly_idx;"
        ),
        
        # Address denormalization for faster shipping queries
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY order_shipping_location_idx ON orders_order (shipping_address_id) INCLUDE (user_id, status, grand_total);",
            reverse_sql="DROP INDEX IF EXISTS order_shipping_location_idx;"
        ),
    ]
"""