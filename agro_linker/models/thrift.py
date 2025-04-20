from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
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

