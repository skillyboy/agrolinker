"""
Marketplace API endpoints for Agro Linker using Django Ninja.
"""
from typing import List, Optional
from ninja import Router, Schema, ModelSchema
from ninja.security import HttpBearer
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth.models import User
from ..models import *
from ..schemas import *
from .auth import AuthBearer
import logging



"""
Marketplace API endpoints for Agro Linker using Django Ninja.
"""
from typing import List, Optional
from ninja import Router, Schema, ModelSchema
from ninja.security import HttpBearer
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest
from django.contrib.auth.models import User
from ..models import *
from ..schemas import *
from .auth import AuthBearer
import logging

# Setup logger for debugging and error logging
logger = logging.getLogger(__name__)

router = Router(tags=["Marketplace"])

# ====================== ENDPOINTS ======================

@router.post("/bids", response=BidOut, auth=AuthBearer(), summary="Place a bid")
@transaction.atomic
def create_bid(request: HttpRequest, payload: BidIn):
    """Place a bid on a product (Buyer only)"""
    
    if not hasattr(request.auth, 'buyer_profile'):
        logger.warning(f"Unauthorized attempt to place bid by user {request.auth.username}")
        return JsonResponse({'error': 'Only buyers can place bids'}, status=403)
    
    product = get_object_or_404(Product, id=payload.product_id)
    
    # Validate bid
    if payload.amount <= product.price:
        logger.info(f"Invalid bid amount {payload.amount} for product {product.id}. Must be higher than {product.price}")
        return JsonResponse({'error': 'Bid amount must be higher than current price'}, status=400)
    
    if payload.quantity > product.quantity:
        logger.info(f"Invalid bid quantity {payload.quantity} for product {product.id}. Available: {product.quantity}")
        return JsonResponse({'error': 'Requested quantity exceeds available amount'}, status=400)
    
    # Create bid
    bid = Bid.objects.create(
        product=product,
        buyer=request.auth,
        **payload.dict(exclude={'product_id'})
    )
    logger.info(f"Bid {bid.id} placed successfully by buyer {request.auth.username} on product {product.id}")
    
    return bid

@router.get("/bids/my", response=List[BidOut], auth=AuthBearer(), summary="Get my bids")
def my_bids(request: HttpRequest):
    """Get all bids placed by the current user"""
    
    # Ensure buyer profile exists for the user
    if not hasattr(request.auth, 'buyer_profile'):
        logger.warning(f"Unauthorized request by user {request.auth.username} to view bids")
        return JsonResponse({'error': 'Unauthorized access. Only buyers can view bids.'}, status=403)
    
    bids = Bid.objects.filter(buyer=request.auth).select_related('product')
    
    if not bids.exists():
        logger.info(f"No bids found for buyer {request.auth.username}")
        return JsonResponse({'message': 'No bids found for this buyer.'}, status=404)
    
    return bids
