from typing import Optional
from pydantic import BaseModel


class RealmData(BaseModel):
    name: str
    id: int


class AuctionData(BaseModel):
    auction_id: int
    item_id: int
    unit_price: Optional[int] = None
    quantity: int
    duration: str
