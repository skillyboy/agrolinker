from ninja import Schema
from datetime import datetime, date
from typing import List, Optional
from agro_linker.models.models import *
from ninja import Schema
from datetime import date
from typing import Optional, List

class CropListingIn(Schema):
    crop_type: str
    quantity: float
    price_per_unit: float
    harvest_date: date
    description: Optional[str] = None
    images: Optional[List[str]] = None

class CropListingOut(Schema):
    id: int
    crop_type: str
    quantity: float
    price_per_unit: float
    status: str
    harvest_date: date
    created_at: datetime

class OfferIn(Schema):
    offered_price: float
    quantity: float
    delivery_date: date
    notes: Optional[str] = None

class OfferOut(Schema):
    id: int
    crop_id: int
    buyer_id: int
    offered_price: float
    status: str
    created_at: datetime

class CropSearchFilters(Schema):
    crop_type: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    location: Optional[str] = None
    radius_km: Optional[int] = None

class TransportRequestIn(Schema):
    contract_id: int
    pickup_location: str
    delivery_location: str
    preferred_vehicle_type: Optional[str] = None
    notes: Optional[str] = None

class TransportRequestOut(Schema):
    id: int
    status: str
    pickup_location: str
    delivery_location: str
    estimated_cost: Optional[float] = None

class LoanApplicationIn(Schema):
    amount: float
    purpose: str
    repayment_period_months: int
    collateral_details: Optional[str] = None

class LoanApplicationOut(Schema):
    id: int
    amount: float
    purpose: str
    status: str
    approval_date: Optional[date] = None

class LoanRepaymentIn(Schema):
    loan_reference: str
    amount: float
    transaction_reference: str
    payment_date: date
    
class UserOut(Schema):
    id: str
    username: str
    email: str

class BuyerProfileOut(Schema):
    id: str
    user_id: str
    location: dict
    verification_status: str
    created_at: datetime    
    updated_at: datetime

class FarmerProfileOut(Schema):
    id: str
    farm_size: float
    verification_status: str
    user_id: str
    location: dict

class FarmerProfileIn(Schema):
    farm_size: float
    location: dict
    user_id: str

class ProductOut(Schema):
    id: str
    name: str
    price: float
    quantity: int
    description: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime

class ProductIn(Schema):
    name: str
    price: float
    quantity: int
    description: Optional[str] = None
    category: Optional[str] = None

class ProductUpdate(Schema):
    status: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None

class OrderItemOut(Schema):
    id: str
    product_id: str
    quantity: int
    unit_price: float

class OrderItemIn(Schema):
    product_id: int
    quantity: int

class OrderOut(Schema):
    id: str
    status: str
    created_at: datetime
    items: List[OrderItemOut] = []
    total_price: float
    delivery_address: str
    delivery_date: datetime
    payment_status: str
    payment_method: str
    payment_date: datetime

class BidOut(Schema):
    id: str
    amount: float
    quantity: int
    status: str
    created_at: datetime

class BidIn(Schema):
    product_id: str
    amount: float
    quantity: int
    delivery_address: str
    delivery_date: str

class StatusUpdate(Schema):
    status: str

class WalletOut(Schema):
    id: str
    balance: float
    created_at: datetime


class WalletIn(Schema):
    amount: float   
    transaction_type: str
    transaction_reference: str
    transaction_date: datetime  

class WalletTransactionOut(Schema):
    id: str
    amount: float
    transaction_type: str
    transaction_reference: str
    transaction_date: datetime  

class ContractOut(Schema):
    id: str
    buyer: UserOut
    farmer: FarmerProfileOut
    product: ProductOut
    quantity: float
    price: float    
    created_at: datetime







class WeatherDataOut(Schema):
    id: int
    location: str
    date: date
    temperature: float
    humidity: float
    precipitation: float
    wind_speed: float
    recorded_at: str

class WeatherDataIn(Schema):
    location: str
    date: date
    temperature: float
    humidity: float
    precipitation: float
    wind_speed: float

class WeatherForecastOut(Schema):
    date: date
    temperature: float
    humidity: float
    precipitation: float
    wind_speed: float

class WeatherFilter(Schema):
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ChatMessageOut(Schema):
    id: str
    sender: UserOut
    receiver: UserOut
    content: str
    timestamp: datetime 

class ChatMessageIn(Schema):
    receiver_id: str
    content: str

class ChatRoomOut(Schema):
    id: str
    participants: List[UserOut]
    created_at: datetime

class ChatRoomIn(Schema):
    participant_ids: List[str]  


class LoanRepaymentOut(Schema):
    id: str
    loan_reference: str
    amount: float
    transaction_reference: str
    payment_date: datetime












