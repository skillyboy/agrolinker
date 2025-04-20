from django.db import models
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
from .market import *
from .models import *
from .base import BaseIntegration

logger = logging.getLogger(__name__)
from django.core.exceptions import ValidationError
from django.db.models import F, Sum



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

