from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            # Composite index for filtering active categories by name
            models.Index(fields=['is_active', 'name'], name='cat_active_name_idx'),
            # Index for date-based queries
            models.Index(fields=['created_at'], name='cat_created_idx'),
            # Partial index for only active categories (more efficient)
            models.Index(
                fields=['name'],
                condition=models.Q(is_active=True),
                name='cat_active_only_idx'
            ),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Most important: category + active status (common filter combination)
            models.Index(fields=['category', 'is_active'], name='prod_cat_active_idx'),
            
            # Price range queries
            models.Index(fields=['price'], name='prod_price_idx'),
            
            # Stock availability queries
            models.Index(fields=['stock'], name='prod_stock_idx'),
            
            # Date-based queries and ordering (supports default ordering)
            models.Index(fields=['-created_at'], name='prod_created_desc_idx'),
            
            # Composite for category + price (common e-commerce query)
            models.Index(fields=['category', 'price'], name='prod_cat_price_idx'),
            
            # Active products with stock (available products)
            models.Index(
                fields=['is_active', 'stock', 'price'],
                name='prod_available_idx'
            ),
            
            # Partial index for in-stock products only
            models.Index(
                fields=['category', 'price'],
                condition=models.Q(stock__gt=0, is_active=True),
                name='prod_avail_cat_price_idx'
            ),
            
            # Text search preparation (if you plan to add search)
            models.Index(fields=['name'], name='prod_name_idx'),
        ]

    def __str__(self):
        return self.name


# Advanced PostgreSQL-specific indexes 
"""
For PostgreSQL-specific optimizations, you could add these in a migration:

from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension

class Migration(migrations.Migration):
    operations = [
        # Enable trigram extension for fuzzy text search
        TrigramExtension(),
        
        # Add trigram index for product name search
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY prod_name_trgm_idx ON myapp_product USING gin (name gin_trgm_ops);",
            reverse_sql="DROP INDEX IF EXISTS prod_name_trgm_idx;"
        ),
        
        # Functional index for price ranges
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY prod_price_range_idx ON myapp_product (CASE WHEN price < 100 THEN 'low' WHEN price < 500 THEN 'medium' ELSE 'high' END);",
            reverse_sql="DROP INDEX IF EXISTS prod_price_range_idx;"
        ),
    ]
"""