from ninja.security import HttpBearer
from django.contrib.auth import authenticate
from django.http import HttpRequest
from typing import Optional

from agro_linker.models import User  # Assuming your User model is here
from agro_linker.schemas import *  # Import relevant schemas


# ====================== AUTH ======================

class RoleBasedAuthBearer(HttpBearer):
    """
    Base class for role-based authentication.
    """
    role_attr: str = ""

    def authenticate(self, request: HttpRequest, token: str) -> Optional[User]:
        user = authenticate(request, token=token)
        if user and hasattr(user, self.role_attr):
            return user
        return None


class UserAuthBearer(RoleBasedAuthBearer):
    """
    Auth for any user (general authentication)
    """
    role_attr = ""  # No role filtering, just general authentication


class AuthBearer(RoleBasedAuthBearer):
    """
    Auth for Farmer or Buyer (either role)
    """
    role_attr = "farmer"  # Can be either 'farmer' or 'buyer', so just check for these roles


class FarmerAuthBearer(RoleBasedAuthBearer):
    """
    Auth for Farmer (only farmer role)
    """
    role_attr = "farmer"


class BuyerAuthBearer(RoleBasedAuthBearer):
    """
    Auth for Buyer (only buyer role)
    """
    role_attr = "buyer"


class AdminAuthBearer(RoleBasedAuthBearer):
    """
    Auth for Admin (only admin role)
    """
    role_attr = "admin"


# Example usage in API endpoints:

from ninja import Router

router = Router(tags=["Auth"])

@router.get("/secure-data", auth=AdminAuthBearer())
def secure_data_for_admin(request: HttpRequest):
    """
    Endpoint only accessible by admin.
    """
    return {"message": "You have access to admin data"}


@router.get("/farmer-data", auth=FarmerAuthBearer())
def farmer_data(request: HttpRequest):
    """
    Endpoint only accessible by farmers.
    """
    return {"message": "You have access to farmer data"}


@router.get("/buyer-data", auth=BuyerAuthBearer())
def buyer_data(request: HttpRequest):
    """
    Endpoint only accessible by buyers.
    """
    return {"message": "You have access to buyer data"}
