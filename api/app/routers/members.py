"""GET /api/members/{member_id}（FR-002）。"""
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_staff
from ..errors import ApiError
from ..repositories import MemberRepository
from ..schemas import MemberOut

router = APIRouter(prefix="/api/members", tags=["members"], dependencies=[Depends(current_staff)])


@router.get("/{member_id}", response_model=MemberOut)
def get_member(
    member_id: Annotated[str, Path(pattern=r"^[A-Za-z0-9\-]{1,20}$")],
    db: Session = Depends(get_db),
):
    m = MemberRepository(db).find(member_id)
    if m is None:
        raise ApiError(404, "MEMBER_NOT_FOUND", "会員が見つかりません")
    return MemberOut(member_id=m.member_id, name=m.name)
