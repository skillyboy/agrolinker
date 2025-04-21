# agro_linker/api/v1/market.py
from ninja import Router
from django.http import HttpRequest
from typing import List, Optional
from agro_linker.schemas import *
from .auth import AuthBearer
from django.shortcuts import get_object_or_404
from agro_linker.models.models import *
from ...schemas import *


router = Router(tags=["Marketplace"])

# ====================== ENDPOINTS ======================
@router.get("/products", response=List[ProductOut], summary="List all products")
def list_products(
    request: HttpRequest,
    farmer_id: Optional[str] = None,
    status: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    """
    List all available products with optional filters:
    - farmer_id: Filter by specific farmer
    - status: Filter by product status
    - min_price/max_price: Price range filtering
    """
    queryset = Product.objects.filter(status='ACTIVE').select_related('farmer')
    
    if farmer_id:
        queryset = queryset.filter(farmer_id=farmer_id)
    if status:
        queryset = queryset.filter(status=status)
    if min_price:
        queryset = queryset.filter(price__gte=min_price)
    if max_price:
        queryset = queryset.filter(price__lte=max_price)
        
    return queryset.order_by('-created_at')

@router.get("/products/{product_id}", response=ProductOut, summary="Get product details")
def get_product(request: HttpRequest, product_id: str):
    """Get detailed information about a specific product"""
    return get_object_or_404(Product, id=product_id)

@router.post("/products", response=ProductOut, auth=AuthBearer(), summary="Create new product")
def create_product(request: HttpRequest, payload: ProductIn):
    """Create a new product listing (Farmer only)"""
    if not hasattr(request.auth, 'farmer_profile'):
        return {'error': 'Only farmers can create products'}, 403
    
    product = Product.objects.create(
        farmer=request.auth.farmer_profile,
        **payload.dict()
    )
    return product

@router.put("/products/{product_id}", response=ProductOut, auth=AuthBearer(), summary="Update product")
def update_product(request: HttpRequest, product_id: str, payload: ProductUpdate):
    """Update product information (Owner only)"""
    product = get_object_or_404(Product, id=product_id)
    
    # Verify ownership
    if product.farmer.user != request.auth:
        return {'error': 'You can only update your own products'}, 403
    
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(product, attr, value)
    
    product.save()
    return product


@router.post('/offers/bulk-discount')
def request_bulk_discount(request, offer_id: int, min_quantity: float, discount: float):
    # Validate quantity and apply dynamic pricing
    offer = get_object_or_404(Offer, id=offer_id)
    if offer.crop.quantity < min_quantity:
        return {'error': 'Insufficient quantity'}, 400
    
    offer.bulk_discount = discount
    offer.save()
    return {'success': 'Bulk discount applied successfully'}

@router.post('/offers/min-quantity')
def request_min_quantity(request, offer_id: int, min_quantity: float):
    # Validate quantity and apply dynamic pricing
    offer = get_object_or_404(Offer, id=offer_id)
    if offer.crop.quantity < min_quantity:
        return {'error': 'Insufficient quantity'}, 400  

    offer.min_quantity = min_quantity
    offer.save()
    return {'success': 'Minimum quantity applied successfully'}

