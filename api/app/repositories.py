"""Repository 層。SQLAlchemy のパラメタバインドのみを使い、生SQLは書かない（NFR-013）。"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Member, Product, Promotion, Staff, TaxRate

JST = timezone(timedelta(hours=9))


def business_date() -> date:
    fixed = get_settings().BUSINESS_DATE
    return fixed or datetime.now(JST).date()


def now_jst_naive() -> datetime:
    """DB には日本時間の naive datetime で保存する。"""
    return datetime.now(JST).replace(tzinfo=None)


class StaffRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_login_id(self, login_id: str) -> Staff | None:
        return self.db.scalar(select(Staff).where(Staff.login_id == login_id))

    def get(self, staff_id: int) -> Staff | None:
        return self.db.get(Staff, staff_id)


class MemberRepository:
    def __init__(self, db: Session):
        self.db = db

    def find(self, member_id: str) -> Member | None:
        return self.db.get(Member, member_id)


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def find(self, code: str) -> Product | None:
        return self.db.get(Product, code)

    def find_many(self, codes: list[str]) -> dict[str, Product]:
        if not codes:
            return {}
        rows = self.db.scalars(select(Product).where(Product.product_code.in_(codes))).all()
        return {p.product_code: p for p in rows}


class TaxRateRepository:
    def __init__(self, db: Session):
        self.db = db

    def current_rates(self, on: date) -> dict[str, TaxRate]:
        """税率区分ごとに、基準日時点で有効な最新の税率を返す（FR-012）。"""
        rows = self.db.scalars(
            select(TaxRate).where(TaxRate.valid_from <= on).order_by(TaxRate.valid_from.desc(), TaxRate.tax_rate_id.desc())
        ).all()
        result: dict[str, TaxRate] = {}
        for r in rows:
            result.setdefault(r.tax_class, r)
        return result


class PromotionRepository:
    def __init__(self, db: Session):
        self.db = db

    def active_for(self, codes: list[str], on: date) -> list[Promotion]:
        if not codes:
            return []
        return list(
            self.db.scalars(
                select(Promotion)
                .where(Promotion.product_code.in_(codes))
                .where(Promotion.start_date <= on)
                .where(Promotion.end_date >= on)
                .order_by(Promotion.promotion_id)
            ).all()
        )
