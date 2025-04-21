from ninja import NinjaAPI, Router, Schema, ModelSchema
from ninja.security import HttpBearer
from typing import List
from django.db import transaction
from django.shortcuts import get_object_or_404
from agro_linker.models.models import *
import logging
from django.http import HttpRequest
from django.contrib.auth import authenticate
from datetime import datetime
from agro_linker.models.models import *
from agro_linker.schemas import *
from ...schemas import *
from .auth import *
from .notification import *
from .chat import *
from .bid import *

# ====================== API SETUP ======================
router = Router(tags=["Orders"])    
logger = logging.getLogger(__name__)



# ====================== AUTH ======================
class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        user = authenticate(request, token=token)
        if user and (hasattr(user, 'farmer') or hasattr(user, 'buyer')):
            return user
        return None



# ====================== ENDPOINTS ======================
@router.get("/", response=List[OrderOut], auth=AuthBearer())
def list_orders(request):
    """List orders filtered by user role"""
    user = request.auth
    if hasattr(user, 'farmer'):
        return Order.objects.filter(farmer=user.farmer).prefetch_related('items')
    elif hasattr(user, 'buyer'):
        return Order.objects.filter(buyer=user.buyer).prefetch_related('items')
    return []

@router.post("/", response={201: OrderOut, 400: dict}, auth=AuthBearer())
@transaction.atomic
def create_order(request, payload: List[OrderItemIn]):
    """Create new order with items"""
    try:
        user = request.auth
        order = Order.objects.create(
            farmer=user.farmer if hasattr(user, 'farmer') else None,
            buyer=user.buyer if hasattr(user, 'buyer') else None
        )
        
        for item in payload:
            product = get_object_or_404(Product, id=item.product_id)
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                unit_price=product.price
            )
        
        order.refresh_from_db()  # Calculate total_price
        return 201, order
    except Exception as e:
        logger.error(f"Order creation failed: {str(e)}")
        return 400, {"detail": "Order processing failed"}

@router.post("/{order_id}/status", response={200: OrderOut, 400: dict}, auth=AuthBearer())
def update_status(request, order_id: int, payload: StatusUpdate):
    """Update order status with validation"""
    order = get_object_or_404(Order, id=order_id)
    
    # Verify ownership
    user = request.auth
    if (hasattr(user, 'farmer') and order.farmer != user.farmer) or \
       (hasattr(user, 'buyer') and order.buyer != user.buyer):
        return 403, {"detail": "Not authorized"}
    
    order.status = payload.status
    order.save()
    return 200, order

@router.post("/{order_id}/items", response={201: OrderItemOut, 400: dict}, auth=AuthBearer())
def add_item(request, order_id: int, payload: OrderItemIn):
    """Add item to existing order"""
    order = get_object_or_404(Order, id=order_id)
    
    # Verify ownership
    user = request.auth
    if not hasattr(user, 'buyer') or order.buyer != user.buyer:
        return 403, {"detail": "Only order buyer can add items"}
    
    try:
        product = Product.objects.get(id=payload.product_id)
        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=payload.quantity,
            unit_price=product.price
        )
        order.refresh_from_db()  # Recalculate total
        return 201, item
    except Product.DoesNotExist:
        return 404, {"detail": "Product not found"}
    

@router.post("/orders/{order_id}/accept", response=OrderOut, auth=AuthBearer(), summary="Accept order")
def accept_order(request: HttpRequest, order_id: str):
    """Accept an order (Farmer only)"""
    order = get_object_or_404(Order, id=order_id)
    
    # Verify ownership
    if order.bid.product.farmer.user != request.auth:
        return {'error': 'You can only accept orders for your products'}, 403
    
    order.status = 'ACCEPTED'
    order.save()
    
    # Update product quantity
    product = order.bid.product
    product.quantity -= order.bid.quantity
    if product.quantity <= 0:
        product.status = 'SOLD'
    product.save()
    
    return order

