"""パスワードハッシュ（bcrypt）と JWT（HS256）。"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings

PASSWORD_MIN_LENGTH = 15  # NFR-009


class PasswordPolicyError(ValueError):
    pass


def hash_password(plain: str) -> str:
    if len(plain) < PASSWORD_MIN_LENGTH:
        raise PasswordPolicyError(f"パスワードは{PASSWORD_MIN_LENGTH}文字以上にしてください")
    # bcrypt は 72 バイトまでしか使わない。仕様上それ以上は想定しないが明示的に切り詰める
    return bcrypt.hashpw(plain.encode("utf-8")[:72], bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("ascii"))
    except ValueError:
        return False


def create_access_token(staff_id: int, login_id: str) -> tuple[str, int]:
    s = get_settings()
    expires = timedelta(minutes=s.ACCESS_TOKEN_EXPIRE_MIN)
    now = datetime.now(timezone.utc)
    payload = {"sub": str(staff_id), "login_id": login_id, "iat": now, "exp": now + expires}
    token = jwt.encode(payload, s.JWT_SECRET, algorithm=s.JWT_ALGORITHM)
    return token, int(expires.total_seconds())


def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.JWT_SECRET, algorithms=[s.JWT_ALGORITHM], options={"require": ["exp", "sub"]})
