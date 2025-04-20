from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import requests
import json
import logging
from time import sleep
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import models
from datetime import datetime

logger = logging.getLogger(__name__)
from django.core.exceptions import ValidationError
from django.db.models import F, Sum

class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Phone number is required')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password):
        user = self.create_user(phone, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        FARMER = 'FARMER', _('Farmer')
        BUYER = 'BUYER', _('Buyer')
        AGENT = 'AGENT', _('Field Agent')
        ADMIN = 'ADMIN', _('Admin')
        LOGISTICS = 'LOGISTICS', _('Logistics Partner')
    
    # Core Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, unique=True, validators=[RegexValidator(r'^\+?1?\d{9,15}$')])
    email = models.EmailField(_('email address'), blank=True, null=True)
    role = models.CharField(max_length=10, choices=Role.choices)
    
    # Profile Fields
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    national_id = models.CharField(max_length=20, blank=True, unique=True)
    profile_photo = models.URLField(blank=True)
    last_location = models.JSONField(null=True)  # {lat, lng, timestamp}
    
    # Status Flags
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    
    # Preferences
    language = models.CharField(max_length=10, choices=[('en', 'English'), ('sw', 'Swahili'), ('fr', 'French')], default='en')
    notification_preferences = models.JSONField(default=dict, blank=True)
    devices = models.JSONField(default=list)  # Track logged-in devices
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['role']
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        indexes = [
            models.Index(fields=['phone', 'is_active']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.phone} ({self.get_role_display()})"




class Cooperative(models.Model):
    name = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=50, unique=True)
    location = models.JSONField(default=dict)  # {lat, lng, address}
    established_date = models.DateField(null=True, blank=True)
    logo = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('cooperative')
        verbose_name_plural = _('cooperatives')
    
    def __str__(self):
        return self.name

class FarmerProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        VERIFIED = 'VERIFIED', _('Verified')
        REJECTED = 'REJECTED', _('Rejected')
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile')
    cooperative = models.ForeignKey(Cooperative, null=True, blank=True, on_delete=models.SET_NULL)
    
    # Farm Details
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.1)])
    location = models.JSONField(default=dict)  # {lat, lng, address}
    soil_type = models.CharField(max_length=50, blank=True, choices=[
        ('clay', _('Clay')), ('sandy', _('Sandy')), ('loamy', _('Loamy'))
    ])
    
    # Agricultural Details
    crops = models.JSONField(default=list, blank=True)  # List of crops grown
    farming_experience = models.PositiveSmallIntegerField(default=0)  # Years
    irrigation_type = models.CharField(max_length=30, blank=True, choices=[
        ('rainfed', _('Rainfed')), ('irrigated', _('Irrigated'))
    ])
    average_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # kg/acre
    
    # Verification
    verification_status = models.CharField(max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
    verification_documents = models.JSONField(null=True, blank=True)  # Encrypted document references
    
    # Financial
    credit_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1000)])
    bank_details = models.JSONField(default=dict)  # Encrypted storage
    
    class Meta:
        verbose_name = _('farmer profile')
        verbose_name_plural = _('farmer profiles')
    
    def calculate_credit_score(self):
        # Implement scoring logic based on transaction history, cooperative membership, etc.
        pass
    
    def __str__(self):
        return f"{self.user.phone}'s Farm Profile"

class BuyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_profile')
    company_name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    business_type = models.CharField(max_length=50, choices=[
        ('retailer', _('Retailer')),
        ('wholesaler', _('Wholesaler')),
        ('processor', _('Processor')),
        ('exporter', _('Exporter'))
    ])
    preferred_crops = models.JSONField(default=list, blank=True)
    purchase_capacity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # Monthly in Naira
    
    class Meta:
        verbose_name = _('buyer profile')
        verbose_name_plural = _('buyer profiles')
    
    def __str__(self):
        return f"{self.company_name} (Buyer)"
    






# ===========================PRODUCT======================================

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

class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.phone} - {self.balance}"

class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10)
    transaction_reference = models.CharField(max_length=100)
    transaction_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user.phone} - {self.amount}"  
    

class Contract(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity     = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)



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

class Vehicle(models.Model):
    class VehicleType(models.TextChoices):
        TRUCK = 'TRUCK', _('Truck')
        PICKUP = 'PICKUP', _('Pickup Truck')
        VAN = 'VAN', _('Van')
        COLD_CHAIN = 'COLD_CHAIN', _('Refrigerated Truck')
        MOTORCYCLE = 'MOTORCYCLE', _('Motorcycle')
    
    plate_number = models.CharField(max_length=15, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices)
    capacity = models.DecimalField(max_digits=10, decimal_places=2)  # in kg
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicles')
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    last_maintenance = models.DateField(null=True, blank=True)
    insurance_details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = _('vehicle')
        verbose_name_plural = _('vehicles')
        ordering = ['vehicle_type', 'plate_number']
    
    def __str__(self):
        return f"{self.get_vehicle_type_display()} ({self.plate_number})"

class LogisticsRequest(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='logistics')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, null=True, blank=True)
    driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Location Details
    pickup_location = models.JSONField()  # {lat, lng, address}
    dropoff_location = models.JSONField()  # {lat, lng, address}
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Timing
    scheduled_pickup = models.DateTimeField()
    scheduled_delivery = models.DateTimeField()
    actual_pickup = models.DateTimeField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    
    # Financial
    transport_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', _('Pending')),
        ('paid', _('Paid')),
        ('partially_paid', _('Partially Paid'))
    ])
    
    # Tracking
    tracking_code = models.CharField(max_length=50, unique=True)
    current_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', _('Pending')),
        ('assigned', _('Assigned')),
        ('in_transit', _('In Transit')),
        ('delivered', _('Delivered')),
        ('cancelled', _('Cancelled'))
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('logistics request')
        verbose_name_plural = _('logistics requests')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Shipment #{self.tracking_code}"

class TrackingStatus(models.Model):
    logistics = models.ForeignKey(LogisticsRequest, on_delete=models.CASCADE, related_name='tracking_history')
    status = models.CharField(max_length=20, choices=[
        ('preparing', _('Preparing Shipment')),
        ('in_transit', _('In Transit')),
        ('delayed', _('Delayed')),
        ('delivered', _('Delivered')),
        ('returned', _('Returned'))
    ])
    location = models.JSONField(null=True, blank=True)  # {lat, lng}
    notes = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('tracking status')
        verbose_name_plural = _('tracking statuses')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.logistics.tracking_code} - {self.get_status_display()}"

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        SMS = 'SMS', _('SMS')
        WHATSAPP = 'WHATSAPP', _('WhatsApp')
        EMAIL = 'EMAIL', _('Email')
        PUSH = 'PUSH', _('Push Notification')
    
    class NotificationStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        SENT = 'SENT', _('Sent')
        FAILED = 'FAILED', _('Failed')
        READ = 'READ', _('Read')
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=10, choices=NotificationType.choices)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=NotificationStatus.choices, default=NotificationStatus.PENDING)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        indexes = [
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.user.phone}"

class FarmerSubscription(models.Model):
    TIER_CHOICES = [
        ('basic', 'Basic (Free)'),
        ('premium', 'Premium (₦5,000/month)'),
        ('enterprise', 'Enterprise (₦15,000/month)')
    ]
    
    farmer = models.OneToOneField(FarmerProfile, on_delete=models.CASCADE, related_name='subscription')
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='basic')
    starts_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    features = models.JSONField(default=list)  # ['priority_listing', 'analytics_dashboard']
    is_active = models.BooleanField(default=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('farmer subscription')
        verbose_name_plural = _('farmer subscriptions')
    
    def __str__(self):
        return f"{self.farmer.user.phone}'s {self.get_tier_display()} Subscription"

class CropCalendar(models.Model):
    crop_type = models.CharField(max_length=100)
    region = models.CharField(max_length=50)  # North/South/West/East
    planting_months = ArrayField(models.IntegerField())  # [1,2,3] for Jan-Mar
    harvesting_months = ArrayField(models.IntegerField())
    optimal_conditions = models.JSONField(default=dict)  # {soil_type, rainfall, temperature}
    
    class Meta:
        verbose_name = _('crop calendar')
        verbose_name_plural = _('crop calendars')
        unique_together = ('crop_type', 'region')
    
    def __str__(self):
        return f"{self.crop_type} Calendar for {self.region}"

class WeatherData(models.Model):
    location = models.CharField(max_length=255)
    date = models.DateField()
    temperature = models.DecimalField(max_digits=5, decimal_places=2)  # Celsius
    humidity = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    precipitation = models.DecimalField(max_digits=5, decimal_places=2)  # mm
    wind_speed = models.DecimalField(max_digits=5, decimal_places=2)  # km/h
    weather_condition = models.CharField(max_length=50)  # sunny, rainy, etc.
    forecast = models.JSONField(default=dict)  # Extended forecast data
    
    class Meta:
        verbose_name = _('weather data')
        verbose_name_plural = _('weather data')
        unique_together = ('location', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"Weather for {self.location} on {self.date}"

class ChatRoom(models.Model):
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message = models.DateTimeField(null=True, blank=True)
    is_group = models.BooleanField(default=False)
    name = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('chat room')
        verbose_name_plural = _('chat rooms')
        ordering = ['-last_message']
    
    def __str__(self):
        if self.is_group:
            return self.name or f"Group Chat {self.id}"
        participants = self.participants.all()
        return f"Chat between {participants[0]} and {participants[1]}"

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = _('chat message')
        verbose_name_plural = _('chat messages')
    
    def __str__(self):
        return f"Message from {self.sender} in {self.room}"

class LoanApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
        ('repaid', 'Repaid'),
        ('defaulted', 'Defaulted')
    ]

    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='loan_applications')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.TextField()
    repayment_period_months = models.PositiveSmallIntegerField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    collateral_details = models.TextField()
    collateral_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    application_date = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    rejection_reason = models.TextField(blank=True)
    reference_id = models.CharField(max_length=20, unique=True)
    
    class Meta:
        verbose_name = _('loan application')
        verbose_name_plural = _('loan applications')
        ordering = ['-application_date']
    
    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = f"LOAN-{self.application_date.strftime('%Y%m%d')}-{str(self.id)[:6]}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Loan #{self.reference_id} - {self.get_status_display()}"

class LoanRepayment(models.Model):
    loan = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, related_name='repayments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_reference = models.CharField(max_length=255)
    payment_method = models.CharField(max_length=20, choices=[
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash')
    ])
    payment_date = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('loan repayment')
        verbose_name_plural = _('loan repayments')
        ordering = ['payment_date']
    
    def __str__(self):
        return f"Repayment of {self.amount} for Loan #{self.loan.reference_id}"

class RepaymentSchedule(models.Model):
    loan = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, related_name='repayment_schedules')
    installment_number = models.PositiveSmallIntegerField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('partially_paid', 'Partially Paid')
    ], default='pending')
    
    class Meta:
        verbose_name = _('repayment schedule')
        verbose_name_plural = _('repayment schedules')
        ordering = ['due_date']
        unique_together = ('loan', 'installment_number')
    
    def __str__(self):
        return f"Installment #{self.installment_number} for Loan #{self.loan.reference_id}"

class SavingsAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_accounts')
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    locked_until = models.DateField(null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('savings account')
        verbose_name_plural = _('savings accounts')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Savings Account #{self.account_number}"

class SavingsTransaction(models.Model):
    account = models.ForeignKey(SavingsAccount, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=[
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('interest', 'Interest'),
        ('transfer', 'Transfer')
    ])
    reference = models.CharField(max_length=100)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('savings transaction')
        verbose_name_plural = _('savings transactions')
        ordering = ['-transaction_date']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} of {self.amount} on {self.transaction_date}"

class CropInsurance(models.Model):
    COVERAGE_TYPES = [
        ('drought', 'Drought'),
        ('flood', 'Flood'),
        ('pest', 'Pest Infestation'),
        ('disease', 'Crop Disease'),
        ('fire', 'Fire')
    ]
    
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='insurance_policies')
    policy_number = models.CharField(max_length=50, unique=True)
    coverage_type = models.CharField(max_length=50, choices=COVERAGE_TYPES)
    crop_type = models.CharField(max_length=100)
    coverage_amount = models.DecimalField(max_digits=12, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    terms = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('crop insurance')
        verbose_name_plural = _('crop insurances')
        ordering = ['-start_date']
    
    def __str__(self):
        return f"Insurance Policy #{self.policy_number}"

class InsuranceClaim(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid')
    ]
    
    insurance = models.ForeignKey(CropInsurance, on_delete=models.CASCADE, related_name='claims')
    claim_amount = models.DecimalField(max_digits=12, decimal_places=2)
    claim_date = models.DateField()
    incident_date = models.DateField()
    description = models.TextField()
    evidence = models.JSONField(default=list)  # List of document URLs
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    decision_date = models.DateTimeField(null=True, blank=True)
    decision_notes = models.TextField(blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('insurance claim')
        verbose_name_plural = _('insurance claims')
        ordering = ['-claim_date']
    
    def __str__(self):
        return f"Claim #{self.id} for Policy #{self.insurance.policy_number}"

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

class ThriftGroup(models.Model):
    name = models.CharField(max_length=100)
    admin = models.ForeignKey(User, on_delete=models.PROTECT, related_name='managed_thrift_groups')
    description = models.TextField(blank=True)
    meeting_schedule = models.CharField(max_length=50)  # "Every 2nd Saturday"
    contribution_amount = models.DecimalField(max_digits=10, decimal_places=2)
    cycle_duration = models.PositiveSmallIntegerField()  # Weeks
    current_cycle = models.PositiveIntegerField(default=1)
    meeting_location = models.JSONField(default=dict)  # {lat, lng, address}
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('thrift group')
        verbose_name_plural = _('thrift groups')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
class ThriftMembership(models.Model):
    group = models.ForeignKey(ThriftGroup, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='thrift_memberships')
    join_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    rotation_order = models.PositiveIntegerField()
    total_contributions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_contribution_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('thrift membership')
        verbose_name_plural = _('thrift memberships')
        unique_together = ('group', 'user')
        ordering = ['rotation_order']
    
    def save(self, *args, **kwargs):
        if not self.rotation_order:
            # Assign next available rotation order
            max_order = ThriftMembership.objects.filter(group=self.group).aggregate(
                max_order=models.Max('rotation_order')
            )['max_order'] or 0
            self.rotation_order = max_order + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.phone} - {self.group.name}"

class ThriftContribution(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', _('Cash')
        TRANSFER = 'TRANSFER', _('Bank Transfer')
        MOBILE_MONEY = 'MOBILE_MONEY', _('Mobile Money')
    
    membership = models.ForeignKey(ThriftMembership, on_delete=models.CASCADE, related_name='contributions')
    cycle = models.PositiveIntegerField(help_text=_("Contribution cycle number"))
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    transaction_reference = models.CharField(max_length=100, unique=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    verified_at = models.DateTimeField(null=True, blank=True)
    date_paid = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('thrift contribution')
        verbose_name_plural = _('thrift contributions')
        ordering = ['-date_paid']
        indexes = [
            models.Index(fields=['transaction_reference']),
            models.Index(fields=['membership', 'cycle']),
        ]
    
    def clean(self):
        if self.amount != self.membership.group.contribution_amount:
            raise ValidationError(_("Contribution amount must match group's set amount"))
    
    def save(self, *args, **kwargs):
        if self.is_verified and not self.verified_at:
            self.verified_at = timezone.now()
            # Update member's total contributions
            self.membership.total_contributions = F('total_contributions') + self.amount
            self.membership.last_contribution_date = self.date_paid
            self.membership.save()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Contribution #{self.id} from {self.membership.user.phone}"

class ThriftPayout(models.Model):
    group = models.ForeignKey(ThriftGroup, on_delete=models.CASCADE, related_name='payouts')
    beneficiary = models.ForeignKey(User, on_delete=models.PROTECT, related_name='thrift_payouts')
    cycle = models.PositiveIntegerField(help_text=_("Payout cycle number"))
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payout_order = models.PositiveSmallIntegerField()
    is_disbursed = models.BooleanField(default=False)
    disbursement_date = models.DateTimeField(null=True, blank=True)
    disbursement_method = models.CharField(max_length=20, choices=ThriftContribution.PaymentMethod.choices, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('thrift payout')
        verbose_name_plural = _('thrift payouts')
        ordering = ['-cycle', 'payout_order']
        unique_together = ('group', 'cycle', 'payout_order')
    
    def __str__(self):
        return f"Payout #{self.id} to {self.beneficiary.phone}"

class ThriftCycle(models.Model):
    group = models.ForeignKey(ThriftGroup, on_delete=models.CASCADE, related_name='cycles')
    cycle_number = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_completed = models.BooleanField(default=False)
    total_contributions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_payouts = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = _('thrift cycle')
        verbose_name_plural = _('thrift cycles')
        unique_together = ('group', 'cycle_number')
        ordering = ['-cycle_number']
    
    def calculate_totals(self):
        self.total_contributions = self.group.contributions.filter(
            cycle=self.cycle_number, is_verified=True
        ).aggregate(total=Sum('amount'))['total'] or 0
        self.total_payouts = self.group.payouts.filter(
            cycle=self.cycle_number, is_disbursed=True
        ).aggregate(total=Sum('amount'))['total'] or 0
        self.save()
    
    def __str__(self):
        return f"Cycle {self.cycle_number} of {self.group.name}"

class ThriftMeeting(models.Model):
    group = models.ForeignKey(ThriftGroup, on_delete=models.CASCADE, related_name='meetings')
    meeting_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    location = models.JSONField(default=dict)  # {lat, lng, address}
    agenda = models.TextField(blank=True)
    minutes = models.TextField(blank=True)
    attendees = models.ManyToManyField(User, through='ThriftAttendance')
    is_regular = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('thrift meeting')
        verbose_name_plural = _('thrift meetings')
        ordering = ['-meeting_date']
    
    def __str__(self):
        return f"Meeting of {self.group.name} on {self.meeting_date}"

class ThriftAttendance(models.Model):
    meeting = models.ForeignKey(ThriftMeeting, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    attended = models.BooleanField(default=False)
    contribution_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('thrift attendance')
        verbose_name_plural = _('thrift attendances')
        unique_together = ('meeting', 'member')
    
    def __str__(self):
        return f"{self.member.phone}'s attendance for {self.meeting}"

class ThriftPenalty(models.Model):
    membership = models.ForeignKey(ThriftMembership, on_delete=models.CASCADE, related_name='penalties')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    cycle = models.PositiveIntegerField()
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('thrift penalty')
        verbose_name_plural = _('thrift penalties')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Penalty of {self.amount} for {self.membership.user.phone}"

class ThriftLoan(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
        ('repaid', 'Repaid'),
        ('defaulted', 'Defaulted')
    ]
    
    group = models.ForeignKey(ThriftGroup, on_delete=models.CASCADE, related_name='loans')
    member = models.ForeignKey(ThriftMembership, on_delete=models.CASCADE, related_name='loans')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.TextField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    repayment_period = models.PositiveSmallIntegerField()  # in weeks
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    application_date = models.DateTimeField(auto_now_add=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    disbursement_date = models.DateTimeField(null=True, blank=True)
    repayment_schedule = models.JSONField(default=list)  # List of repayment dates/amounts
    guarantors = models.ManyToManyField(ThriftMembership, related_name='guaranteed_loans')
    
    class Meta:
        verbose_name = _('thrift loan')
        verbose_name_plural = _('thrift loans')
        ordering = ['-application_date']
    
    def generate_repayment_schedule(self):
        # Implement repayment schedule generation
        pass
    
    def __str__(self):
        return f"Loan #{self.id} for {self.member.user.phone}"

class ThriftLoanRepayment(models.Model):
    loan = models.ForeignKey(ThriftLoan, on_delete=models.CASCADE, related_name='repayments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    installment_number = models.PositiveSmallIntegerField()
    due_date = models.DateField()
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=ThriftContribution.PaymentMethod.choices)
    transaction_reference = models.CharField(max_length=100)
    is_late = models.BooleanField(default=False)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = _('thrift loan repayment')
        verbose_name_plural = _('thrift loan repayments')
        ordering = ['loan', 'installment_number']
    
    def __str__(self):
        return f"Repayment #{self.installment_number} for Loan #{self.loan.id}"



class BaseIntegration:
    """Base class for all integration services"""
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self, provider):
        self.provider = provider
        self.config = self._get_provider_config()
        
    def _get_provider_config(self):
        """Get configuration for the specified provider"""
        config_key = f"{self.CONFIG_NAMESPACE}_PROVIDERS"
        return getattr(settings, config_key, {}).get(self.provider, {})
    
    def _make_request(self, method, url, **kwargs):
        """Generic request method with retry logic"""
        headers = kwargs.pop('headers', {})
        headers.update(self._get_default_headers())
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    timeout=self.config.get('timeout', 30),
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(f"Request failed after {self.MAX_RETRIES} attempts: {str(e)}")
                    raise
                sleep(self.RETRY_DELAY * (attempt + 1))
    
    def _get_default_headers(self):
        """Get default headers for the provider"""
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

class MobileMoneyProcessor(BaseIntegration):
    CONFIG_NAMESPACE = 'MOBILE_MONEY'
    
    def collect_contribution(self, phone, amount, reference):
        """Process mobile money payment"""
        try:
            processor_method = getattr(self, f'_process_{self.provider.lower()}', None)
            if processor_method:
                return processor_method(phone, amount, reference)
            raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"Mobile money processing failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'provider': self.provider
            }
    
    def _process_mtn(self, phone, amount, reference):
        payload = {
            'subscriber': phone,
            'amount': str(amount),
            'reference': reference,
            'callback_url': self.config.get('callback_url')
        }
        return self._make_request(
            'POST',
            self.config.get('api_url'),
            json=payload,
            headers={
                'Authorization': f"Bearer {self.config.get('api_key')}"
            }
        )
    
    def _process_airtel(self, phone, amount, reference):
        payload = {
            'msisdn': phone,
            'amount': str(amount),
            'transaction_id': reference,
            'callback': self.config.get('callback_url')
        }
        return self._make_request(
            'POST',
            self.config.get('api_url'),
            data=payload,
            headers={
                'Authorization': f"Basic {self.config.get('api_key')}"
            }
        )
    
    def verify_transaction(self, transaction_id):
        """Verify a mobile money transaction"""
        try:
            verifier_method = getattr(self, f'_verify_{self.provider.lower()}', None)
            if verifier_method:
                return verifier_method(transaction_id)
            raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"Transaction verification failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'provider': self.provider
            }
    
    def _verify_mtn(self, transaction_id):
        return self._make_request(
            'GET',
            f"{self.config.get('api_url')}/{transaction_id}",
            headers={
                'Authorization': f"Bearer {self.config.get('api_key')}"
            }
        )
    
    def _verify_airtel(self, transaction_id):
        return self._make_request(
            'GET',
            f"{self.config.get('api_url')}/status/{transaction_id}",
            headers={
                'Authorization': f"Basic {self.config.get('api_key')}"
            }
        )

class SMSGateway(BaseIntegration):
    CONFIG_NAMESPACE = 'SMS'
    
    def send_sms(self, phone, message):
        """Send SMS message"""
        try:
            sender_method = getattr(self, f'_send_{self.provider.lower()}', None)
            if sender_method:
                return sender_method(phone, message)
            raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'provider': self.provider
            }
    
    def _send_africastalking(self, phone, message):
        payload = {
            'username': self.config.get('username'),
            'to': phone,
            'message': message,
            'from': self.config.get('sender_id')
        }
        return self._make_request(
            'POST',
            self.config.get('api_url'),
            data=payload,
            headers={
                'apiKey': self.config.get('api_key'),
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
    
    def _send_twilio(self, phone, message):
        payload = {
            'To': phone,
            'From': self.config.get('sender_id'),
            'Body': message
        }
        return self._make_request(
            'POST',
            self.config.get('api_url'),
            data=payload,
            auth=(self.config.get('account_sid'), self.config.get('auth_token'))
        )

class EmailService(BaseIntegration):
    CONFIG_NAMESPACE = 'EMAIL'
    
    def send_email(self, to, subject, body, html_body=None):
        """Send email with optional HTML content"""
        try:
            sender_method = getattr(self, f'_send_{self.provider.lower()}', None)
            if sender_method:
                return sender_method(to, subject, body, html_body)
            raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'provider': self.provider
            }
    
    def _send_sendgrid(self, to, subject, body, html_body=None):
        content = [{
            'type': 'text/plain',
            'value': body
        }]
        if html_body:
            content.append({
                'type': 'text/html',
                'value': html_body
            })
        
        payload = {
            'personalizations': [{
                'to': [{'email': to}],
                'subject': subject
            }],
            'from': {'email': self.config.get('from_email')},
            'content': content
        }
        return self._make_request(
            'POST',
            self.config.get('api_url'),
            json=payload,
            headers={
                'Authorization': f"Bearer {self.config.get('api_key')}"
            }
        )
    
    def _send_mailgun(self, to, subject, body, html_body=None):
        data = {
            'from': self.config.get('from_email'),
            'to': to,
            'subject': subject,
            'text': body
        }
        if html_body:
            data['html'] = html_body
        
        return self._make_request(
            'POST',
            self.config.get('api_url'),
            auth=('api', self.config.get('api_key')),
            data=data
        )

class AgroAnalytics(models.Model):
    """Consolidated platform analytics data"""
    date = models.DateField(unique=True)
    active_farmers = models.PositiveIntegerField(default=0)
    active_buyers = models.PositiveIntegerField(default=0)
    products_listed = models.PositiveIntegerField(default=0)
    transactions_completed = models.PositiveIntegerField(default=0)
    total_transaction_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_product_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    new_registrations = models.PositiveIntegerField(default=0)
    thrift_groups_active = models.PositiveIntegerField(default=0)
    loans_disbursed = models.PositiveIntegerField(default=0)
    loan_amount_disbursed = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = _('agro analytics')
        verbose_name_plural = _('agro analytics')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
        ]
    
    @classmethod
    def generate_daily_report(cls):
        """Generate daily analytics report"""
        from django.db.models import Count, Sum, Avg
        from django.utils import timezone
        
        today = timezone.now().date()
        
        # Prevent duplicate entries
        if cls.objects.filter(date=today).exists():
            return
        
        # Calculate metrics
        from .models import (
            User, Product, Order, 
            ThriftGroup, LoanApplication
        )
        
        metrics = {
            'date': today,
            'active_farmers': User.objects.filter(
                role=User.Role.FARMER, 
                is_active=True
            ).count(),
            'active_buyers': User.objects.filter(
                role=User.Role.BUYER, 
                is_active=True
            ).count(),
            'products_listed': Product.objects.filter(
                status=Product.Status.ACTIVE
            ).count(),
            'transactions_completed': Order.objects.filter(
                payment_status=Order.PaymentStatus.PAID,
                created_at__date=today
            ).count(),
            'thrift_groups_active': ThriftGroup.objects.filter(
                is_active=True
            ).count(),
            'loans_disbursed': LoanApplication.objects.filter(
                status='disbursed',
                disbursement_date__date=today
            ).count()
        }
        
        # Transaction values
        transaction_data = Order.objects.filter(
            payment_status=Order.PaymentStatus.PAID,
            created_at__date=today
        ).aggregate(
            total_value=Sum(F('bid__amount') * F('bid__quantity')),
            avg_price=Avg('bid__amount')
        )
        
        metrics.update({
            'total_transaction_value': transaction_data['total_value'] or 0,
            'average_product_price': transaction_data['avg_price'] or 0
        })
        
        # Loan amounts
        loan_data = LoanApplication.objects.filter(
            status='disbursed',
            disbursement_date__date=today
        ).aggregate(
            total_amount=Sum('amount')
        )
        
        metrics.update({
            'loan_amount_disbursed': loan_data['total_amount'] or 0
        })
        
        # New registrations
        metrics['new_registrations'] = User.objects.filter(
            created_at__date=today
        ).count()
        
        # Create analytics record
        cls.objects.create(**metrics)
    
    def __str__(self):
        return f"Analytics for {self.date}"

class SystemSettings(models.Model):
    """Configuration settings for the platform"""
    key = models.CharField(max_length=50, unique=True)
    value = models.JSONField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('system setting')
        verbose_name_plural = _('system settings')
        ordering = ['key']
    
    @classmethod
    def get_setting(cls, key, default=None):
        try:
            setting = cls.objects.get(key=key, is_active=True)
            return setting.value
        except cls.DoesNotExist:
            return default
    
    def __str__(self):
        return self.key

class AuditLog(models.Model):
    """System activity log for tracking important actions"""
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('payment', 'Payment'),
        ('verification', 'Verification'),
        ('api_call', 'API Call'),
    ]
    
    user = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model', 'object_id']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    @classmethod
    def log_action(cls, **kwargs):
        """Helper method to create audit log entries"""
        try:
            return cls.objects.create(**kwargs)
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
    
    def __str__(self):
        return f"{self.get_action_display()} on {self.model} by {self.user or 'System'}"