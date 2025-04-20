from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import requests
import logging
from django.conf import settings
from datetime import datetime
from .user import User, FarmerProfile
# from .market import *
from .thrift import ThriftGroup
from .finance import *
from .chat import *

logger = logging.getLogger(__name__)
from django.core.exceptions import ValidationError
from django.db.models import F, Sum

# [Rest of the models.py content, including Cooperative, Vehicle, LogisticsRequest, etc., remains unchanged]
# For brevity, only showing the imports and necessary context

class Cooperative(models.Model):
    name = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=50, unique=True)
    location = models.JSONField(default=dict)
    established_date = models.DateField(null=True, blank=True)
    logo = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('cooperative')
        verbose_name_plural = _('cooperatives')
    
    def __str__(self):
        return self.name

# [Other models like Vehicle, LogisticsRequest, etc., follow]


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