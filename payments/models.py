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
