from decimal import Decimal
from django.db import transaction
from django.utils.timezone import now
from rest_framework import serializers
from products.models import Product
from .models import Address, Order, OrderItem

# --- Address ---
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"

# --- Order Items ---
class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("id", "product", "name", "unit_price", "quantity", "line_total")

# --- Order Read Serializers ---
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    billing_address = AddressSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id", "number", "status", "currency",
            "subtotal", "discount_total", "tax_total", "shipping_total", "grand_total",
            "payment_reference",
            "shipping_address", "billing_address",
            "items", "created_at", "updated_at",
        )

# --- Order Create ---
class OrderCreateSerializer(serializers.Serializer):
    # simple fixed-rate tax/shipping for demo; replace with real calculator later
    currency = serializers.CharField(default="USD")
    items = OrderItemCreateSerializer(many=True)
    shipping_address = AddressSerializer()
    billing_address = AddressSerializer()
    # optional: coupon code, notes, etc.

    def validate(self, data):
        if not data["items"]:
            raise serializers.ValidationError({"items": "At least one item is required."})
        return data

    def _generate_order_number(self) -> str:
        dt = now()
        return f"ORD-{dt.strftime('%Y')}-{dt.strftime('%m%d%H%M%S')}-{dt.strftime('%f')[:3]}"

    @transaction.atomic
    def create(self, validated):
        request = self.context["request"]
        user = request.user
        idempotency_key = request.headers.get("Idempotency-Key")  # optional

        # handle idempotency
        if idempotency_key:
            existing = Order.objects.filter(idempotency_key=idempotency_key, user=user).first()
            if existing:
                return existing

        # lock products for stock checks
        product_ids = [i["product_id"] for i in validated["items"]]
        products = (Product.objects.select_for_update()
                    .filter(id__in=product_ids, is_active=True))
        product_map = {p.id: p for p in products}
        if len(product_map) != len(product_ids):
            raise serializers.ValidationError({"items": "One or more products are invalid or inactive."})

        # stock + price snapshot
        subtotal = Decimal("0.00")
        prepared_items = []
        for item in validated["items"]:
            p = product_map[item["product_id"]]
            qty = item["quantity"]
            if p.stock < qty:
                raise serializers.ValidationError({"items": f"Insufficient stock for {p.name}."})
            line_total = (p.price * qty).quantize(Decimal("0.01"))
            subtotal += line_total
            prepared_items.append((p, qty, line_total))

        # simplistic tax/shipping; swap for your calculator later
        tax_total = (subtotal * Decimal("0.16")).quantize(Decimal("0.01"))  # e.g., 16% VAT (KE example)
        shipping_total = Decimal("5.00") if subtotal < Decimal("100.00") else Decimal("0.00")
        discount_total = Decimal("0.00")
        grand_total = (subtotal - discount_total + tax_total + shipping_total).quantize(Decimal("0.01"))

        # persist addresses (snapshot)
        ship_addr = Address.objects.create(**validated["shipping_address"])
        bill_addr = Address.objects.create(**validated["billing_address"])

        # create order
        order = Order.objects.create(
            user=user,
            number=self._generate_order_number(),
            status=Order.Status.PENDING,
            shipping_address=ship_addr,
            billing_address=bill_addr,
            currency=validated["currency"],
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            shipping_total=shipping_total,
            grand_total=grand_total,
            idempotency_key=idempotency_key or None,
        )

        # create items + decrement stock
        bulk_items = []
        for p, qty, line_total in prepared_items:
            bulk_items.append(OrderItem(
                order=order,
                product=p,
                name=p.name,                # snapshot
                unit_price=p.price,         # snapshot
                quantity=qty,
                line_total=line_total
            ))
            p.stock -= qty
        OrderItem.objects.bulk_create(bulk_items)
        Product.objects.bulk_update(products, ["stock"])

        return order
