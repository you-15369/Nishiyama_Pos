"""AuthService：担当ID・パスワードによる認証（FR-001, NFR-008, NFR-009, NFR-011）。

ログイン失敗によるロックアウトは行わない（試行回数の制限なし）。
"""
import bcrypt
from sqlalchemy.orm import Session

from ..errors import ApiError
from ..models import Staff
from ..repositories import StaffRepository
from ..security import verify_password

# 存在しないIDでも照合時間を揃えるためのダミーハッシュ（ユーザー列挙対策）
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password-for-timing", bcrypt.gensalt()).decode("ascii")

INVALID = ("INVALID_CREDENTIALS", "IDまたはパスワードが正しくありません")


class AuthService:
    def __init__(self, db: Session):
        self.staff = StaffRepository(db)

    def authenticate(self, login_id: str, password: str) -> Staff:
        staff = self.staff.find_by_login_id(login_id)
        if staff is None:
            verify_password(password, _DUMMY_HASH)
            raise ApiError(401, *INVALID)
        if not verify_password(password, staff.password_hash):
            raise ApiError(401, *INVALID)
        return staff
