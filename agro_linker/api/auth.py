from ninja.security import HttpBearer
from django.contrib.auth import authenticate
from agro_linker.models import *
from agro_linker.api.schemas import *
from django.shortcuts import get_object_or_404
from django.http import HttpRequest
from typing import List
ProductOut

from ninja import Router

router = Router(tags=["Auth"])

# ====================== AUTH ======================
class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        user = authenticate(request, token=token)
        if user and (hasattr(user, 'farmer') or hasattr(user, 'buyer')):
            return user
        return None
    
class FarmerAuthBearer(HttpBearer):
    def authenticate(self, request, token):
        user = authenticate(request, token=token)
        if user and hasattr(user, 'farmer'):
            return user
        return None
    
class BuyerAuthBearer(HttpBearer):
    def authenticate(self, request, token):
        user = authenticate(request, token=token)
        if user and hasattr(user, 'buyer'):
            return user
        return None
    
class AdminAuthBearer(HttpBearer):
    def authenticate(self, request, token):
        user = authenticate(request, token=token)
        if user and hasattr(user, 'admin'):
            return user
        return None

class UserAuthBearer(HttpBearer):
    def authenticate(self, request, token):
        user = authenticate(request, token=token)
        if user:
            return user
        return 

    


    
    

