"""POST /api/transactions（FR-009, FR-010）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_staff
from ..models import Staff
from ..schemas import TransactionRequest
from ..services.transaction import TransactionService

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post("", status_code=201)
def create_transaction(
    body: TransactionRequest,
    staff: Staff = Depends(current_staff),
    db: Session = Depends(get_db),
) -> dict:
    out = TransactionService(db).confirm(staff.staff_id, body)
    return {"data": out.model_dump(mode="json")}
