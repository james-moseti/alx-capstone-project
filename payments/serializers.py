from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = (
            "id",
            "user",
            "amount",
            "currency",
            "status",
            "transaction_id",
            "raw_response",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        """
        On creation:
        - Automatically set user = request.user
        - Fill amount and currency from the linked order
        - Always start with status = PENDING
        """
        request = self.context["request"]
        validated_data["user"] = request.user

        order = validated_data["order"]
        validated_data["amount"] = order.grand_total
        validated_data["currency"] = order.currency
        validated_data["status"] = Payment.Status.PENDING

        return super().create(validated_data)
