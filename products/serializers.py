from rest_framework import serializers
from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


# Lightweight serializer (for list)
class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"   # category appears as ID only


# Detailed serializer (for retrieve)
class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)  # nested details
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True
    )

    class Meta:
        model = Product
        fields = "__all__"
