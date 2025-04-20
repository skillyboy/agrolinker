from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from .models import LoanApplication, LoanRepayment, FarmerProfile
from .schemas import LoanApplicationIn, LoanApplicationOut, LoanRepaymentIn, LoanRepaymentOut
from typing import List
from .auth import AuthBearer
from .notification import notify_loan_update

from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

api = Router(tags=["Microfinance"])





import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from .models import LoanApplication, LoanRepayment, FarmerProfile, RepaymentSchedule
from .schemas import LoanApplicationIn, LoanApplicationOut, LoanRepaymentIn, LoanRepaymentOut
from typing import List
import uuid
import json

logger = logging.getLogger(__name__)

# Helper Functions Implementation
def generate_loan_reference():
    """Generate unique loan reference in format: LN-YYYYMMDD-XXXXX"""
    today = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:5].upper()
    return f"LN-{today}-{unique_id}"

def create_repayment_schedule(loan: LoanApplication):
    """
    Create amortized repayment schedule for the loan
    """
    if loan.repayment_period_months <= 0:
        raise ValueError("Invalid repayment period")
    
    repayment_amount = loan.amount / loan.repayment_period_months
    due_date = datetime.now() + timedelta(days=30)  # First payment due in 30 days
    
    schedules = []
    for i in range(loan.repayment_period_months):
        schedules.append(
            RepaymentSchedule(
                loan=loan,
                installment_number=i+1,
                due_date=due_date + timedelta(days=30*i),
                amount=repayment_amount,
                status='pending'
            )
        )
    
    RepaymentSchedule.objects.bulk_create(schedules)

def verify_webhook_signature(request: HttpRequest) -> bool:
    """
    Verify HMAC signature from MFI webhook
    """
    if not settings.MFI_WEBHOOK_SECRET:
        logger.error("MFI_WEBHOOK_SECRET not configured")
        return False
    
    signature = request.headers.get('X-MFI-Signature')
    if not signature:
        return False
    
    try:
        body = request.body.decode('utf-8')
        expected_signature = hmac.new(
            key=settings.MFI_WEBHOOK_SECRET.encode(),
            msg=body.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Signature verification failed: {str(e)}")
        return False

def log_repayment_error(payload: LoanRepaymentIn, error: str):
    """
    Log repayment processing errors with context
    """
    error_data = {
        "timestamp": datetime.now().isoformat(),
        "loan_reference": payload.loan_reference,
        "transaction_reference": payload.transaction_reference,
        "amount": payload.amount,
        "error": error
    }
    logger.error(json.dumps(error_data))

# API Endpoints Implementation
@api.post("/loans/apply", auth=AuthBearer(), response={201: LoanApplicationOut, 400: dict})
def apply_for_loan(request, payload: LoanApplicationIn):
    """
    Submit a loan application
    Required: amount, purpose, repayment_period_months
    Optional: collateral_details
    """
    farmer = get_object_or_404(FarmerProfile, user=request.user)
    
    if LoanApplication.objects.filter(farmer=farmer, status='pending').exists():
        raise HttpError(400, "You already have a pending application")
    
    max_loan_amount = farmer.get_credit_limit()
    if payload.amount > max_loan_amount:
        raise HttpError(400, f"Amount exceeds your credit limit of {max_loan_amount}")
    
    try:
        with transaction.atomic():
            loan = LoanApplication.objects.create(
                farmer=farmer,
                **payload.dict(),
                status='pending',
                reference_id=generate_loan_reference()
            )
            create_repayment_schedule(loan)
            return 201, loan
    except Exception as e:
        logger.error(f"Loan application failed: {str(e)}")
        raise HttpError(400, "Failed to process loan application")

@method_decorator(csrf_exempt, name='dispatch')
@api.post("/loans/repay", response={200: dict, 400: dict, 404: dict}, auth=None)
def record_repayment(request, payload: LoanRepaymentIn):
    """
    Webhook for MFI to record repayments
    """
    if not verify_webhook_signature(request):
        raise HttpError(401, "Unauthorized")
    
    try:
        with transaction.atomic():
            loan = get_object_or_404(
                LoanApplication, 
                reference_id=payload.loan_reference,
                status__in=['approved', 'partially_paid']
            )
            
            if LoanRepayment.objects.filter(
                transaction_reference=payload.transaction_reference
            ).exists():
                raise HttpError(400, "Duplicate transaction detected")
            
            repayment = LoanRepayment.objects.create(
                loan=loan,
                amount=payload.amount,
                transaction_reference=payload.transaction_reference,
                payment_date=payload.payment_date,
                payment_method=payload.payment_method
            )
            
            # Update repayment schedule
            update_repayment_schedule(loan, repayment)
            
            # Update loan status
            loan.amount_paid = (loan.amount_paid or 0) + payload.amount
            if loan.amount_paid >= loan.amount:
                loan.status = 'repaid'
            else:
                loan.status = 'partially_paid'
            loan.save()
            
            return 200, {
                "success": True,
                "balance": max(0, loan.amount - loan.amount_paid)
            }
            
    except Exception as e:
        log_repayment_error(payload, str(e))
        raise HttpError(400, f"Payment processing failed: {str(e)}")

def update_repayment_schedule(loan: LoanApplication, repayment: LoanRepayment):
    """
    Update repayment schedule when payment is received
    """
    remaining_amount = repayment.amount
    schedules = loan.repayment_schedules.filter(
        status='pending'
    ).order_by('due_date')
    
    for schedule in schedules:
        if remaining_amount <= 0:
            break
        
        payment_amount = min(schedule.amount, remaining_amount)
        schedule.amount_paid = (schedule.amount_paid or 0) + payment_amount
        
        if schedule.amount_paid >= schedule.amount:
            schedule.status = 'paid'
        
        schedule.save()
        remaining_amount -= payment_amount

# Additional Helper Functions
def notify_loan_update(loan: LoanApplication):
    """
    Send notification about loan status update
    """
    # Implementation would depend on your notification system
    # Could be email, SMS, or push notification
    notification_message = (
        f"Loan {loan.reference_id} update: "
        f"Status changed to {loan.status}. "
        f"Amount paid: {loan.amount_paid}/{loan.amount}"
    )
    
    # Example using Django's async task system
    from .tasks import send_notification
    send_notification.delay(
        user_id=loan.farmer.user.id,
        message=notification_message
    )








@api.post("/loans/apply", auth=AuthBearer(), response={201: LoanApplicationOut, 400: dict})
def apply_for_loan(request, payload: LoanApplicationIn):
    """
    Submit a loan application
    Required: amount, purpose, repayment_period_months
    Optional: collateral_details
    """
    farmer = get_object_or_404(FarmerProfile, user=request.user)
    
    # Check for pending applications using exists() for better performance
    if LoanApplication.objects.filter(farmer=farmer, status='pending').exists():
        raise HttpError(400, "You already have a pending application")
    
    # Validate loan amount against farmer's potential (could be moved to serializer)
    max_loan_amount = farmer.get_credit_limit()  # Assuming this method exists
    if payload.amount > max_loan_amount:
        raise HttpError(400, f"Amount exceeds your credit limit of {max_loan_amount}")
    
    with transaction.atomic():
        loan = LoanApplication.objects.create(
            farmer=farmer,
            **payload.dict(),
            status='pending',
            reference_id=generate_loan_reference()  # Implement this function
        )
        
        # Initialize repayment schedule
        create_repayment_schedule(loan)  # Implement this function
    
    return 201, loan

@api.get("/loans/status", auth=AuthBearer(), response=List[LoanApplicationOut])
def check_loan_status(request):
    """
    Get all loan applications for the farmer with optimized query
    """
    farmer = get_object_or_404(FarmerProfile, user=request.user)
    loans = LoanApplication.objects.filter(
        farmer=farmer
    ).select_related('farmer').only(
        'id', 'amount', 'purpose', 'status', 
        'application_date', 'approval_date'
    ).order_by('-application_date')
    
    return loans

@api.post("/loans/repay", 
          response={200: dict, 400: dict, 404: dict},
          auth=None)  # Public endpoint for webhooks
def record_repayment(request, payload: LoanRepaymentIn):
    """
    Webhook for MFI to record repayments
    Includes HMAC signature verification for security
    """
    # Verify webhook signature (implement verify_webhook_signature)
    if not verify_webhook_signature(request):
        raise HttpError(401, "Unauthorized")
    
    try:
        with transaction.atomic():
            loan = get_object_or_404(
                LoanApplication, 
                reference_id=payload.loan_reference,
                status__in=['approved', 'partially_paid']
            )
            
            # Prevent duplicate transactions
            if LoanRepayment.objects.filter(
                transaction_reference=payload.transaction_reference
            ).exists():
                raise HttpError(400, "Duplicate transaction detected")
            
            repayment = LoanRepayment.objects.create(
                loan=loan,
                amount=payload.amount,
                transaction_reference=payload.transaction_reference,
                payment_date=payload.payment_date,
                payment_method=payload.payment_method
            )
            
            # Update loan status atomically
            loan.amount_paid = (loan.amount_paid or 0) + payload.amount
            if loan.amount_paid >= loan.amount:
                loan.status = 'repaid'
            else:
                loan.status = 'partially_paid'
            loan.save()
            
            # Trigger notification
            notify_loan_update(loan)  # Implement this function
            
            return 200, {
                "success": True,
                "balance": loan.amount - loan.amount_paid
            }
            
    except Exception as e:
        log_repayment_error(payload, str(e))  # Implement this function
        raise HttpError(400, f"Payment processing failed: {str(e)}")

@api.get("/loans/history", 
         auth=AuthBearer(), 
         response=List[LoanApplicationOut])
def loan_history(request):
    """
    Get complete loan history for farmer with pagination
    """
    farmer = get_object_or_404(FarmerProfile, user=request.user)
    loans = LoanApplication.objects.filter(
        farmer=farmer
    ).prefetch_related(
        'repayments'
    ).select_related(
        'farmer'
    ).only(
        'id', 'amount', 'purpose', 'status',
        'application_date', 'approval_date', 'amount_paid'
    ).order_by('-application_date')
    
    return loans

@api.get("/loans/{loan_id}/repayments", 
         auth=AuthBearer(),
         response=List[LoanRepaymentOut])
def get_loan_repayments(request, loan_id: int):
    """
    Get all repayments for a specific loan
    """
    farmer = get_object_or_404(FarmerProfile, user=request.user)
    loan = get_object_or_404(
        LoanApplication, 
        id=loan_id, 
        farmer=farmer
    )
    
    return loan.repayments.all().order_by('payment_date')

