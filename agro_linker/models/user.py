from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.translation import gettext_lazy as _
import uuid

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
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, unique=True, validators=[RegexValidator(r'^\+?1?\d{9,15}$')])
    email = models.EmailField(_('email address'), blank=True, null=True)
    role = models.CharField(max_length=10, choices=Role.choices)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    national_id = models.CharField(max_length=20, blank=True, unique=True)
    profile_photo = models.URLField(blank=True)
    last_location = models.JSONField(null=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    language = models.CharField(max_length=10, choices=[('en', 'English'), ('sw', 'Swahili'), ('fr', 'French')], default='en')
    notification_preferences = models.JSONField(default=dict, blank=True)
    devices = models.JSONField(default=list)
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

class FarmerProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        VERIFIED = 'VERIFIED', _('Verified')
        REJECTED = 'REJECTED', _('Rejected')
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile')
    cooperative = models.ForeignKey('models.Cooperative', null=True, blank=True, on_delete=models.SET_NULL)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.1)])
    location = models.JSONField(default=dict)
    soil_type = models.CharField(max_length=50, blank=True, choices=[
        ('clay', _('Clay')), ('sandy', _('Sandy')), ('loamy', _('Loamy'))
    ])
    crops = models.JSONField(default=list, blank=True)
    farming_experience = models.PositiveSmallIntegerField(default=0)
    irrigation_type = models.CharField(max_length=30, blank=True, choices=[
        ('rainfed', _('Rainfed')), ('irrigated', _('Irrigated'))
    ])
    average_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    verification_status = models.CharField(max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
    verification_documents = models.JSONField(null=True, blank=True)
    credit_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1000)])
    bank_details = models.JSONField(default=dict)
    
    class Meta:
        verbose_name = _('farmer profile')
        verbose_name_plural = _('farmer profiles')
    
    def calculate_credit_score(self):
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
    purchase_capacity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    class Meta:
        verbose_name = _('buyer profile')
        verbose_name_plural = _('buyer profiles')
    
    def __str__(self):
        return f"{self.company_name} (Buyer)"