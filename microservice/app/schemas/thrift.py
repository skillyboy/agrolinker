from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# microservice/app/schemas/thrift.py

from pydantic import BaseModel

class ThriftRequest(BaseModel):
    data: str

class ThriftResponse(BaseModel):
    message: str
