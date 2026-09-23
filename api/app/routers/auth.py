"""POST /api/auth/login ほか（FR-001）。"""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import COOKIE_NAME, current_staff
from ..models import Staff
from ..schemas import LoginRequest, LoginResponse, StaffOut
from ..security import create_access_token
from ..services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _staff_out(s: Staff) -> StaffOut:
    return StaffOut(staff_id=s.staff_id, login_id=s.login_id, name=s.name)


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    staff = AuthService(db).authenticate(body.login_id, body.password)
    token, expires_in = create_access_token(staff.staff_id, staff.login_id)
    # API を直接呼ぶ場合（テスト等）のために Cookie でも払い出す。本番はBFFが HttpOnly Cookie で保持する
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=expires_in,
        httponly=True,
        secure=get_settings().is_prod,
        samesite="lax",
        path="/",
    )
    return LoginResponse(access_token=token, expires_in=expires_in, staff=_staff_out(staff))


@router.get("/me", response_model=StaffOut)
def me(staff: Staff = Depends(current_staff)):
    return _staff_out(staff)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    response.status_code = 204
    return response
