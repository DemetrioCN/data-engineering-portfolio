from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class PaymentMethod(str, Enum):
    cash     = "cash"
    card     = "card"


class VisitEvent(BaseModel):
    date:              str
    customer_id:       str
    route_id:          str
    order_id:          str
    warehouse_code:    str
    quantity:          int
    delivery_quantity: Optional[int]           = None
    arrival_time:      Optional[datetime]      = None
    departure_time:    Optional[datetime]      = None
    signature_time:    Optional[datetime]      = None
    payment_method:    Optional[PaymentMethod] = None