# microservice/app/api/__init__.py

from fastapi import APIRouter
from .v1 import farm

router = APIRouter()

router.include_router(farm.router, prefix="/v1/farm", tags=["Farm"])
