


from .models import Contract, BuyerProfile
from .schemas import ContractOut, CropSearchFilters


from django.db import transaction
from datetime import datetime
from ninja import NinjaAPI, Schema, ModelSchema, Query
from ninja.security import HttpBearer
from typing import List, Optional
from .models import CropListing, Offer, FarmerProfile, TransportRequest
from .schemas import CropListingIn, CropListingOut, OfferIn, OfferOut, TransportRequestIn, TransportRequestOut

api = NinjaAPI()

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "valid_token":
            return token

# Farmer Crop Management
@api.post("/farmers/crops", auth=AuthBearer(), response=CropListingOut)
def create_crop_listing(request, payload: CropListingIn):
    """
    Create a new crop listing
    Required fields: crop_type, quantity, price_per_unit, harvest_date
    Optional: description, images (array of URLs)
    """
    farmer = FarmerProfile.objects.get(user=request.user)
    crop = CropListing.objects.create(
        farmer=farmer,
        **payload.dict()
    )
    return crop

@api.get("/farmers/crops", auth=AuthBearer(), response=List[CropListingOut])
def list_farmer_crops(request, status: Optional[str] = None):
    """
    Get all crops listed by the authenticated farmer
    Query params: status (available/sold/contracted)
    """
    farmer = FarmerProfile.objects.get(user=request.user)
    crops = CropListing.objects.filter(farmer=farmer)
    
    if status:
        crops = crops.filter(status=status.lower())
    
    return crops

@api.patch("/farmers/crops/{crop_id}", auth=AuthBearer(), response=CropListingOut)
def update_crop_listing(request, crop_id: int, payload: CropListingIn):
    """
    Update a crop listing (only owner can update)
    Can update: quantity, price, status, description
    """
    farmer = FarmerProfile.objects.get(user=request.user)
    crop = CropListing.objects.get(id=crop_id, farmer=farmer)
    
    for attr, value in payload.dict().items():
        if value is not None:
            setattr(crop, attr, value)
    
    crop.save()
    return crop

@api.delete("/farmers/crops/{crop_id}", auth=AuthBearer())
def delete_crop_listing(request, crop_id: int):
    """
    Delete a crop listing (only if no active offers)
    """
    farmer = FarmerProfile.objects.get(user=request.user)
    crop = CropListing.objects.get(id=crop_id, farmer=farmer)
    
    if crop.offers.filter(status='pending').exists():
        return {"error": "Cannot delete - pending offers exist"}
    
    crop.delete()
    return {"success": True}

# Farmer Offer Management
@api.get("/farmers/offers", auth=AuthBearer(), response=List[OfferOut])
def list_farmer_offers(request, crop_id: Optional[int] = None):
    """
    Get all offers for farmer's crops
    Optional filter by specific crop
    """
    farmer = FarmerProfile.objects.get(user=request.user)
    offers = Offer.objects.filter(crop__farmer=farmer)
    
    if crop_id:
        offers = offers.filter(crop_id=crop_id)
    
    return offers

@api.post("/farmers/offers/{offer_id}/accept", auth=AuthBearer(), response=OfferOut)
def respond_to_offer(request, offer_id: int, accept: bool):
    """
    Accept or reject a buyer offer
    Body: {"accept": true/false}
    """
    with transaction.atomic():
        farmer = FarmerProfile.objects.get(user=request.user)
        offer = Offer.objects.select_for_update().get(
            id=offer_id,
            crop__farmer=farmer,
            status='pending'
        )
        
        if accept:
            offer.status = 'accepted'
            offer.crop.status = 'contracted'
            offer.crop.save()
            # Create contract here
        else:
            offer.status = 'rejected'
        
        offer.save()
        return offer







@api.get("/buyers/crops", response=List[CropListingOut])
def browse_crops(request, filters: CropSearchFilters = Query(...)):
    """
    Search and filter crop listings
    Query params: crop_type, min_price, max_price, location, radius_km
    """
    crops = CropListing.objects.filter(status='available')
    
    if filters.crop_type:
        crops = crops.filter(crop_type__iexact=filters.crop_type)
    
    if filters.min_price:
        crops = crops.filter(price_per_unit__gte=filters.min_price)
    
    if filters.max_price:
        crops = crops.filter(price_per_unit__lte=filters.max_price)
    
    if filters.location and filters.radius_km:
        # Implement geo-distance filtering
        pass
    
    return crops

@api.post("/buyers/crops/{crop_id}/offer", auth=AuthBearer(), response=OfferOut)
def submit_offer(request, crop_id: int, payload: OfferIn):
    """
    Submit an offer for a crop listing
    Required: offered_price, quantity, delivery_date
    """
    buyer = BuyerProfile.objects.get(user=request.user)
    crop = CropListing.objects.get(id=crop_id, status='available')
    
    if payload.quantity > crop.quantity:
        return {"error": "Requested quantity exceeds available"}
    
    offer = Offer.objects.create(
        buyer=buyer,
        crop=crop,
        **payload.dict()
    )
    return offer

@api.get("/buyers/contracts", auth=AuthBearer(), response=List[ContractOut])
def list_buyer_contracts(request, active_only: bool = True):
    """
    Get buyer's contracts
    Query param: active_only (true/false)
    """
    buyer = BuyerProfile.objects.get(user=request.user)
    contracts = Contract.objects.filter(buyer=buyer)
    
    if active_only:
        contracts = contracts.filter(status__in=['pending', 'fulfilling'])
    
    return contracts

@api.post("/buyers/contracts/{contract_id}/cancel", auth=AuthBearer(), response=ContractOut)
def cancel_contract(request, contract_id: int, reason: str):
    """
    Request contract cancellation
    Body: {"reason": "..."}
    """
    buyer = BuyerProfile.objects.get(user=request.user)
    contract = Contract.objects.get(id=contract_id, buyer=buyer)
    
    if contract.status not in ['pending', 'fulfilling']:
        return {"error": "Cannot cancel - contract already completed or cancelled"}
    
    contract.status = 'cancellation_requested'
    contract.cancellation_reason = reason
    contract.save()
    return contract

@router.get("/farmers/{farmer_id}", response=FarmerProfileOut, summary="Get farmer profile")
def get_farmer(request: HttpRequest, farmer_id: str):
    """Get public profile of a farmer"""
    return get_object_or_404(FarmerProfile, id=farmer_id)

@router.get("/farmers/{farmer_id}/products", response=List[ProductOut], summary="Get farmer's products")
def farmer_products(request: HttpRequest, farmer_id: str):
    """Get all active products from a specific farmer"""
    return Product.objects.filter(
        farmer_id=farmer_id,
        status='ACTIVE'
    ).order_by('-created_at')
