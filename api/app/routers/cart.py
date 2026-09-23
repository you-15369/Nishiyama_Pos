"""POST /api/cart/price（FR-007, FR-008）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_staff
from ..schemas import PriceRequest, Quote
from ..services.pricing import PricingService

router = APIRouter(prefix="/api/cart", tags=["cart"], dependencies=[Depends(current_staff)])


@router.post("/price")
def price(body: PriceRequest, db: Session = Depends(get_db)) -> dict:
    quote, _ = PricingService(db).quote(body.member_id, body.items)
    return {"data": quote.model_dump(mode="json")}
