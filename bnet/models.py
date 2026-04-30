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


class ItemData(BaseModel):
    id: int
    name: str
    item_class_id: int
    item_subclass_id: int
    stackable: bool
    quality: Optional[str] = None
    purchase_price: Optional[int] = None
    sell_price: Optional[int] = None
    media: Optional[int] = None


class ItemClassData(BaseModel):
    id: int
    name: str


class ItemSubclassData(BaseModel):
    id: int
    class_id: int
    name: str


class ListingStats(BaseModel):
    min_price: int | None
    median_price: int | None
    market_value: int | None
    quantity_listed: int
    auction_count: int
    avg_stack: float
