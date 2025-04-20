from datetime import datetime
from typing import List, Optional

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.security import HttpBearer
from ninja import Query
from ninja import Router
from ..models.models import *
from ..schemas import *

# Create a router instead of a new API instance
router = Router(tags=["Farm"])


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "valid_token":
            return token


# Farmer Crop Management
@router.post("/farmers/crops", auth=AuthBearer(), response=CropListingOut)
def create_crop_listing(request, payload: CropListingIn):
    """Create a new crop listing"""
    try:
        farmer = FarmerProfile.objects.get(user=request.user)
        crop = CropListing.objects.create(farmer=farmer, **payload.dict())
        return crop
    except FarmerProfile.DoesNotExist:
        return JsonResponse({"error": "Farmer profile not found."}, status=404)


@router.get("/farmers/crops", auth=AuthBearer(), response=List[CropListingOut])
def list_farmer_crops(request, status: Optional[str] = None):
    """List all crops listed by the authenticated farmer"""
    try:
        farmer = FarmerProfile.objects.get(user=request.user)
        crops = CropListing.objects.filter(farmer=farmer)
        if status:
            crops = crops.filter(status=status.lower())
        return crops
    except FarmerProfile.DoesNotExist:
        return JsonResponse({"error": "Farmer profile not found."}, status=404)


@router.patch("/farmers/crops/{crop_id}", auth=AuthBearer(), response=CropListingOut)
def update_crop_listing(request, crop_id: int, payload: CropListingIn):
    """Update a crop listing owned by the authenticated farmer"""
    try:
        farmer = FarmerProfile.objects.get(user=request.user)
        crop = CropListing.objects.get(id=crop_id, farmer=farmer)
        for attr, value in payload.dict().items():
            if value is not None:
                setattr(crop, attr, value)
        crop.save()
        return crop
    except FarmerProfile.DoesNotExist:
        return JsonResponse({"error": "Farmer profile not found."}, status=404)
    except CropListing.DoesNotExist:
        return JsonResponse({"error": "Crop listing not found."}, status=404)


@router.delete("/farmers/crops/{crop_id}", auth=AuthBearer())
def delete_crop_listing(request, crop_id: int):
    """Delete a crop listing if no active offers exist"""
    try:
        farmer = FarmerProfile.objects.get(user=request.user)
        crop = CropListing.objects.get(id=crop_id, farmer=farmer)
        if crop.offers.filter(status='pending').exists():
            return JsonResponse({"error": "Cannot delete - pending offers exist."}, status=400)
        crop.delete()
        return JsonResponse({"success": True})
    except FarmerProfile.DoesNotExist:
        return JsonResponse({"error": "Farmer profile not found."}, status=404)
    except CropListing.DoesNotExist:
        return JsonResponse({"error": "Crop listing not found."}, status=404)


# Farmer Offer Management
@router.get("/farmers/offers", auth=AuthBearer(), response=List[OfferOut])
def list_farmer_offers(request, crop_id: Optional[int] = None):
    """List offers for the farmer's crops"""
    try:
        farmer = FarmerProfile.objects.get(user=request.user)
        offers = Offer.objects.filter(crop__farmer=farmer)
        if crop_id:
            offers = offers.filter(crop_id=crop_id)
        return offers
    except FarmerProfile.DoesNotExist:
        return JsonResponse({"error": "Farmer profile not found."}, status=404)


@router.post("/farmers/offers/{offer_id}/accept", auth=AuthBearer(), response=OfferOut)
def respond_to_offer(request, offer_id: int, accept: bool):
    """Accept or reject a buyer's offer"""
    try:
        with transaction.atomic():
            farmer = FarmerProfile.objects.get(user=request.user)
            offer = Offer.objects.select_for_update().get(id=offer_id, crop__farmer=farmer, status='pending')
            if accept:
                offer.status = 'accepted'
                offer.crop.status = 'contracted'
                offer.crop.save()
                # Contract creation can be handled here
            else:
                offer.status = 'rejected'
            offer.save()
            return offer
    except FarmerProfile.DoesNotExist:
        return JsonResponse({"error": "Farmer profile not found."}, status=404)
    except Offer.DoesNotExist:
        return JsonResponse({"error": "Offer not found or already responded."}, status=404)


# Buyer Crop Browsing
@router.get("/buyers/crops", response=List[CropListingOut])
def browse_crops(request, filters: CropSearchFilters = Query(...)):
    """Search and filter crop listings"""
    crops = CropListing.objects.filter(status='available')
    if filters.crop_type:
        crops = crops.filter(crop_type__iexact=filters.crop_type)
    if filters.min_price:
        crops = crops.filter(price_per_unit__gte=filters.min_price)
    if filters.max_price:
        crops = crops.filter(price_per_unit__lte=filters.max_price)
    if filters.location and filters.radius_km:
        # TODO: Implement geo-distance filtering logic
        pass
    return crops


@router.post("/buyers/crops/{crop_id}/offer", auth=AuthBearer(), response=OfferOut)
def submit_offer(request, crop_id: int, payload: OfferIn):
    """Submit an offer for a crop listing"""
    try:
        buyer = BuyerProfile.objects.get(user=request.user)
        crop = CropListing.objects.get(id=crop_id, status='available')
        if payload.quantity > crop.quantity:
            return JsonResponse({"error": "Requested quantity exceeds available."}, status=400)
        offer = Offer.objects.create(buyer=buyer, crop=crop, **payload.dict())
        return offer
    except BuyerProfile.DoesNotExist:
        return JsonResponse({"error": "Buyer profile not found."}, status=404)
    except CropListing.DoesNotExist:
        return JsonResponse({"error": "Crop listing not found or unavailable."}, status=404)


@router.get("/buyers/contracts", auth=AuthBearer(), response=List[ContractOut])
def list_buyer_contracts(request, active_only: bool = True):
    """List buyer's contracts"""
    try:
        buyer = BuyerProfile.objects.get(user=request.user)
        contracts = Contract.objects.filter(buyer=buyer)
        if active_only:
            contracts = contracts.filter(status__in=['pending', 'fulfilling'])
        return contracts
    except BuyerProfile.DoesNotExist:
        return JsonResponse({"error": "Buyer profile not found."}, status=404)


@router.post("/buyers/contracts/{contract_id}/cancel", auth=AuthBearer(), response=ContractOut)
def cancel_contract(request, contract_id: int, reason: str):
    """Request cancellation of a contract"""
    try:
        buyer = BuyerProfile.objects.get(user=request.user)
        contract = Contract.objects.get(id=contract_id, buyer=buyer)
        if contract.status not in ['pending', 'fulfilling']:
            return JsonResponse({"error": "Cannot cancel - contract already completed or cancelled."}, status=400)
        contract.status = 'cancellation_requested'
        contract.cancellation_reason = reason
        contract.save()
        return contract
    except BuyerProfile.DoesNotExist:
        return JsonResponse({"error": "Buyer profile not found."}, status=404)
    except Contract.DoesNotExist:
        return JsonResponse({"error": "Contract not found."}, status=404)


@router.get("/farmers/{farmer_id}", response=FarmerProfileOut)
def get_farmer(request, farmer_id: str):
    """Get public profile of a farmer"""
    return get_object_or_404(FarmerProfile, id=farmer_id)


@router.get("/farmers/{farmer_id}/products", response=List[ProductOut])
def farmer_products(request, farmer_id: str):
    """List all active products for a farmer"""
    return Product.objects.filter(farmer_id=farmer_id, status='ACTIVE').order_by('-created_at')