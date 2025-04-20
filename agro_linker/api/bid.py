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
from .schemas import *
from .auth import AuthBearer
import logging

router = Router(tags=["Marketplace"])


# ====================== ENDPOINTS ======================


@router.post("/bids", response=BidOut, auth=AuthBearer(), summary="Place a bid")
@transaction.atomic
def create_bid(request: HttpRequest, payload: BidIn):
    """Place a bid on a product (Buyer only)"""
    if not hasattr(request.auth, 'buyer_profile'):
        return {'error': 'Only buyers can place bids'}, 403
    
    product = get_object_or_404(Product, id=payload.product_id)
    
    # Validate bid
    if payload.amount <= product.price:
        return {'error': 'Bid amount must be higher than current price'}, 400
    if payload.quantity > product.quantity:
        return {'error': 'Requested quantity exceeds available amount'}, 400
    
    bid = Bid.objects.create(
        product=product,
        buyer=request.auth,
        **payload.dict(exclude={'product_id'})
    )
    
    return bid

@router.get("/bids/my", response=List[BidOut], auth=AuthBearer(), summary="Get my bids")
def my_bids(request: HttpRequest):
    """Get all bids placed by the current user"""
    return Bid.objects.filter(buyer=request.auth).select_related('product')

