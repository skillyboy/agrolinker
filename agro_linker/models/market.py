from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import logging
from django.conf import settings
from datetime import datetime
from .user import User, FarmerProfile
from .finance import *


logger = logging.getLogger(__name__)
from django.core.exceptions import ValidationError
from django.db.models import F, Sum


class ProductCategory(models.Model):
    name = models.CharField(max_length=50)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    image = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('product category')
        verbose_name_plural = _('product categories')
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ACTIVE = 'ACTIVE', _('Active')
        RESERVED = 'RESERVED', _('Reserved')
        SOLD = 'SOLD', _('Sold')
        EXPIRED = 'EXPIRED', _('Expired')
    
    class QualityGrade(models.TextChoices):
        GRADE_A = 'A', _('Grade A')
        GRADE_B = 'B', _('Grade B')
        GRADE_C = 'C', _('Grade C')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT)
    
    # Core Product Info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    variety = models.CharField(max_length=100, blank=True)
    
    # Pricing & Quantity
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    unit = models.CharField(max_length=10, choices=[
        ('kg', _('Kilogram')), ('g', _('Gram')), ('ton', _('Metric Ton'))
    ], default='kg')
    minimum_order = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_conversion = models.JSONField(
        default={'kg': 1, 'g': 1000, 'ton': 0.001},
        help_text="Conversion rates for different units"
    )
    
    # Quality & Status
    quality_grade = models.CharField(max_length=1, choices=QualityGrade.choices, blank=True)
    organic_certified = models.BooleanField(default=False)
    organic_certificate_id = models.CharField(max_length=50, blank=True)
    harvest_date = models.DateField(null=True, blank=True)
    harvest_method = models.CharField(max_length=50, blank=True)
    storage_conditions = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('product')
        verbose_name_plural = _('products')
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['price']),
            models.Index(fields=['farmer', 'status']),
        ]
    
    def clean(self):
        if self.quantity <= 0 and self.status == self.Status.ACTIVE:
            raise ValidationError(_("Active products must have quantity > 0"))
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_images')
    image_url = models.URLField()
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('product image')
        verbose_name_plural = _('product images')
        ordering = ['-is_primary', 'uploaded_at']
    
    def __str__(self):
        return f"Image for {self.product.name}"

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('product review')
        verbose_name_plural = _('product reviews')
        ordering = ['-created_at']
        unique_together = ('product', 'reviewer')
    
    def __str__(self):
        return f"{self.rating}★ review for {self.product.name}"


class CropListing(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.farmer.phone} - {self.product.name}"


class Bid(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.buyer.phone} - {self.product.name}"
    
class Offer(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        ACCEPTED = 'ACCEPTED', _('Accepted')
        REJECTED = 'REJECTED', _('Rejected')
        WITHDRAWN = 'WITHDRAWN', _('Withdrawn')
        EXPIRED = 'EXPIRED', _('Expired')
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers_made')
    
    # Offer Details
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    delivery_address = models.TextField()
    delivery_date = models.DateField()
    bulk_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    min_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Status Management
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('offer')
        verbose_name_plural = _('offers')
        indexes = [
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['product', 'status']),
            models.Index(fields=['buyer', 'status']),
        ]
    
    def clean(self):
        if self.amount <= self.product.price:
            raise ValidationError(_("Bid amount must be higher than product price"))
        if self.quantity > self.product.quantity:
            raise ValidationError(_("Bid quantity exceeds available product quantity"))
    
    def __str__(self):
        return f"Offer #{self.id} for {self.product.name}"

class Order(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        ESCROW = 'ESCROW', _('Escrow Held')
        PAID = 'PAID', _('Paid')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')
    
    bid = models.OneToOneField(Offer, on_delete=models.PROTECT, related_name='order')
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=20, blank=True, choices=[
        ('mobile_money', _('Mobile Money')),
        ('bank_transfer', _('Bank Transfer')),
        ('cash', _('Cash'))
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('order')
        verbose_name_plural = _('orders')
        indexes = [
            models.Index(fields=['payment_status']),
        ]
    
    def total_amount(self):
        return self.bid.amount * self.bid.quantity
    
    def __str__(self):
        return f"Order #{self.id} ({self.get_payment_status_display()})"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = _('order item')
        verbose_name_plural = _('order items')
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class PriceTrend(models.Model):
    crop_type = models.CharField(max_length=50)
    market = models.CharField(max_length=100)
    date = models.DateField()
    avg_price = models.DecimalField(max_digits=10, decimal_places=2)
    min_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_price = models.DecimalField(max_digits=10, decimal_places=2)
    predicted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_unit = models.CharField(max_length=10, default='kg')
    source = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('price trend')
        verbose_name_plural = _('price trends')
        ordering = ['-date']
        unique_together = ('crop_type', 'market', 'date')
    
    def __str__(self):
        return f"{self.crop_type} price at {self.market} on {self.date}"




