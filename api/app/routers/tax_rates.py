"""GET /api/tax-rates（FR-008, FR-012）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_staff
from ..repositories import TaxRateRepository, business_date

router = APIRouter(prefix="/api/tax-rates", tags=["tax-rates"], dependencies=[Depends(current_staff)])


@router.get("")
def tax_rates(db: Session = Depends(get_db)) -> dict:
    rows = TaxRateRepository(db).current_rates(business_date())
    return {
        "data": [
            {"tax_class": cls, "rate": float(r.rate), "valid_from": r.valid_from.isoformat()}
            for cls, r in sorted(rows.items())
        ]
    }
