from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.services.farm_service import FarmService
from app.schemas.farm import Farm, FarmCreate, FarmUpdate
from app.core.security import get_current_user


from fastapi import APIRouter
from app.services.thrift_service import process_thrift_data
from app.schemas.thrift import ThriftRequest, ThriftResponse

router = APIRouter()

@router.post("/process-thrift", response_model=ThriftResponse)
async def process_thrift(request: ThriftRequest):
    result = process_thrift_data(request.data)
    return ThriftResponse(message=result["message"])


@router.get("/", response_model=List[Farm])
def list_farms(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all farms"""
    return FarmService.get_farms(db, skip, limit)

@router.post("/", response_model=Farm)
def create_farm(
    farm: FarmCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new farm"""
    return FarmService.create_farm(db, farm, current_user.id) 
