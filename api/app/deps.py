"""共通の依存性：認証済み担当者の取得（全業務APIでトークン検証。未認証は401）。"""
import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .db import get_db
from .errors import ApiError
from .models import Staff
from .repositories import StaffRepository
from .security import decode_access_token

COOKIE_NAME = "pos_token"


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return request.cookies.get(COOKIE_NAME)


def current_staff(request: Request, db: Session = Depends(get_db)) -> Staff:
    token = _extract_token(request)
    if not token:
        raise ApiError(401, "UNAUTHORIZED", "ログインが必要です")
    try:
        payload = decode_access_token(token)
        staff_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise ApiError(401, "UNAUTHORIZED", "認証の有効期限が切れたか、トークンが不正です")
    staff = StaffRepository(db).get(staff_id)
    if staff is None:
        raise ApiError(401, "UNAUTHORIZED", "ログインが必要です")
    return staff
