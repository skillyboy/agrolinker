from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import HttpRequest
from agro_linker.models.models import Product, Order, FarmerProfile
from agro_linker.api.auth import AuthBearer  # Assuming you have a proper auth implementation
from ...schemas import *
from datetime import datetime
from django.db.models import Q
from ninja import Router
from agro_linker.models.models import ChatMessage
from .auth import AuthBearer
import logging

router = Router(tags=["Chat"])
logger = logging.getLogger(__name__)

# ====================== ENDPOINTS ======================

def get_user_profile(request: HttpRequest):
    if hasattr(request.auth, 'farmer_profile'):
        profile = request.auth.farmer_profile
        return {
            'id': str(profile.id),
            'user_id': str(profile.user.id),
            'location': profile.location,
            'verification_status': profile.verification_status,
            'created_at': profile.created_at,
            'updated_at': profile.updated_at,
            'profile_type': 'farmer',
            'farm_size': profile.farm_size,
            'company_name': None
        }
    elif hasattr(request.auth, 'buyer_profile'):
        profile = request.auth.buyer_profile
        return {
            'id': str(profile.id),
            'user_id': str(profile.user.id),
            'location': profile.location,
            'verification_status': profile.verification_status,
            'created_at': profile.created_at,
            'updated_at': profile.updated_at,
            'profile_type': 'buyer',
            'farm_size': None,
            'company_name': profile.company_name
        }
    return None

def get_chat_history(request: HttpRequest, user_id: str):
    user_profile = get_user_profile(request)
    if not user_profile:
        return {'error': 'User profile not found'}, 404
    
    # Get chat history between current user and target user
    chat_history = ChatMessage.objects.filter(
        Q(sender=user_profile) | Q(receiver=user_profile),
        Q(sender=user_id) | Q(receiver=user_id)
    ).order_by('timestamp')
    
    return [ChatMessageOut.from_orm(msg) for msg in chat_history]       

@router.post("/send_message", response=ChatMessageOut, auth=AuthBearer())
def send_message(request: HttpRequest, payload: ChatMessageIn):
    user_profile = get_user_profile(request)
    if not user_profile:
        return {'error': 'User profile not found'}, 404
    
    message = ChatMessage.objects.create(
        sender=user_profile,
        receiver=payload.receiver_id,
        content=payload.content,
        timestamp=datetime.now()
    )   
    return ChatMessageOut.from_orm(message)         

