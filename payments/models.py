from django.conf import settings
from django.db import models
from orders.models import Order


class Payment(models.Model):
    class Provider(models.TextChoices):
        MANUAL = "manual", "Manual"
        PAYPAL = "paypal", "PayPal"
        STRIPE = "stripe", "Stripe"
        MPESA = "mpesa", "M-Pesa"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.MANUAL)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=100, blank=True)  # e.g. PayPal txn id
    raw_response = models.JSONField(blank=True, null=True)  # full API payload for auditing

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # Critical: payment status monitoring (most frequent query)
            models.Index(fields=['status', '-created_at'], name='payment_status_created_idx'),
            
            # User payment history
            models.Index(fields=['user', '-created_at'], name='payment_user_created_idx'),
            models.Index(fields=['user', 'status'], name='payment_user_status_idx'),
            
            # Provider-specific queries (payment processing, reconciliation)
            models.Index(fields=['provider', 'status'], name='payment_provider_status_idx'),
            models.Index(fields=['provider', '-created_at'], name='payment_provider_created_idx'),
            
            # Transaction tracking and lookups
            models.Index(fields=['transaction_id'], name='payment_transaction_idx'),
            
            # Financial reporting - amount-based queries
            models.Index(fields=['currency', 'status', 'created_at'], name='payment_currency_status_idx'),
            models.Index(fields=['amount'], name='payment_amount_idx'),
            
            # Failed payments analysis (for fraud detection, debugging)
            models.Index(
                fields=['provider', '-created_at'],
                condition=models.Q(status='FAILED'),
                name='payment_failed_provider_idx'
            ),
            
            # Successful payments for revenue reporting
            models.Index(
                fields=['-created_at', 'amount', 'currency'],
                condition=models.Q(status='SUCCESS'),
                name='payment_success_revenue_idx'
            ),
            
            # Pending payments monitoring (requires attention)
            models.Index(
                fields=['-created_at'],
                condition=models.Q(status='PENDING'),
                name='payment_pending_recent_idx'
            ),
            
            # Refund tracking
            models.Index(
                fields=['provider', '-created_at'],
                condition=models.Q(status='REFUNDED'),
                name='payment_refunded_idx'
            ),
            
            # High-value transactions (for special handling/monitoring)
            models.Index(
                fields=['-amount', '-created_at'],
                condition=models.Q(amount__gte=1000),
                name='payment_high_value_idx'
            ),
            
            # Recent activity across all statuses
            models.Index(fields=['-updated_at'], name='payment_updated_idx'),
            
            # Provider-specific transaction lookups
            models.Index(
                fields=['provider', 'transaction_id'],
                condition=models.Q(transaction_id__isnull=False),
                name='payment_provider_txn_idx'
            ),
            
            # Daily reconciliation queries
            models.Index(
                fields=['created_at', 'provider', 'status'],
                name='payment_daily_recon_idx'
            ),
        ]

    def __str__(self):
        return f"Payment {self.id} - {self.provider} - {self.status}"

    def mark_successful(self, transaction_id=None, raw=None):
        """Mark payment as successful and update order status"""
        self.status = self.Status.SUCCESS
        if transaction_id:
            self.transaction_id = transaction_id
        if raw:
            self.raw_response = raw
        self.save(update_fields=["status", "transaction_id", "raw_response", "updated_at"])
        self.order.status = Order.Status.PAID
        self.order.save(update_fields=["status", "updated_at"])

    def mark_failed(self, raw=None):
        """Mark payment as failed"""
        self.status = self.Status.FAILED
        if raw:
            self.raw_response = raw
        self.save(update_fields=["status", "raw_response", "updated_at"])


# Additional optimizations for payment processing
"""
Advanced indexes you might add via migration for high-volume payment processing:

from django.db import migrations
from django.contrib.postgres.operations import BtreeGinExtension
from django.contrib.postgres.indexes import GinIndex

class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0001_initial'),
    ]
    
    operations = [
        BtreeGinExtension(),
        
        # JSON search on raw_response for debugging/auditing
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY payment_raw_response_gin_idx ON payments_payment USING gin (raw_response);",
            reverse_sql="DROP INDEX IF EXISTS payment_raw_response_gin_idx;"
        ),
        
        # Time-series partitioning for high volume
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY payment_hourly_stats_idx ON payments_payment (date_trunc('hour', created_at), provider, status);",
            reverse_sql="DROP INDEX IF EXISTS payment_hourly_stats_idx;"
        ),
        
        # Covering index for payment dashboard queries
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY payment_dashboard_idx ON payments_payment (status, created_at) INCLUDE (provider, amount, currency);",
            reverse_sql="DROP INDEX IF EXISTS payment_dashboard_idx;"
        ),
        
        # Unique constraint on successful payments per provider transaction
        migrations.RunSQL(
            "CREATE UNIQUE INDEX CONCURRENTLY payment_provider_txn_success_idx ON payments_payment (provider, transaction_id) WHERE status = 'SUCCESS' AND transaction_id IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS payment_provider_txn_success_idx;"
        ),
    ]
"""
