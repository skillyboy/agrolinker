from sqlalchemy.orm import Session
from app.models.farm import Farm
from app.schemas.farm import FarmCreate, FarmUpdate
from fastapi import HTTPException
from typing import List




# microservice/app/services/thrift_service.py

def process_thrift_data(data: str) -> dict:
    # Simulate some processing logic
    return {"message": f"Processed: {data}"}







class FarmService:
    @staticmethod
    def get_farms(db: Session, skip: int = 0, limit: int = 100) -> List[Farm]:
        return db.query(Farm).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_farm(db: Session, farm_id: int) -> Farm:
        farm = db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            raise HTTPException(status_code=404, detail="Farm not found")
        return farm
    
    @staticmethod
    def create_farm(db: Session, farm: FarmCreate, owner_id: int) -> Farm:
        db_farm = Farm(**farm.dict(), owner_id=owner_id)
        db.add(db_farm)
        db.commit()
        db.refresh(db_farm)
        return db_farm 