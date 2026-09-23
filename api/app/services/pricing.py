"""PricingService：金額・値引き・税の計算をここに集約する（NFR-012）。

ルール
- 値引きは会員に限り、企画対象の商品・期間内のときだけ、1個あたりで適用する（R-011, FR-007）。
  会員でない会計（member_id=null）には値引きを一切適用しない。
  - 割合: floor(単価 × 率 / 100)
  - 金額: min(値引き額, 単価)  ← 単価で頭打ちにしてマイナスにしない（UT-BE-04）
  - 同じ商品に複数の企画がある場合は、1個あたり値引きが最大のものを1つだけ使う
- 税額は税率区分ごとに（値引き後の税抜合計 × 税率）を floor（切り捨て）で計算する（TAX_ROUNDING=floor）
- 税込合計 = 値引き後の税抜合計 + 区分別税額の合計
"""
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from sqlalchemy.orm import Session

from ..errors import ApiError
from ..repositories import (
    MemberRepository,
    ProductRepository,
    PromotionRepository,
    TaxRateRepository,
    business_date,
)
from ..schemas import CartItemIn, PriceLine, Quote, TaxByClass


@dataclass(frozen=True)
class ProductInfo:
    product_code: str
    name: str
    unit_price: int
    tax_class: str


@dataclass(frozen=True)
class PromotionInfo:
    product_code: str
    discount_type: str  # rate / amount
    discount_value: int


def unit_discount(unit_price: int, promo: PromotionInfo) -> int:
    if promo.discount_type == "rate":
        value = (Decimal(unit_price) * Decimal(promo.discount_value) / Decimal(100)).to_integral_value(ROUND_FLOOR)
        return max(0, min(int(value), unit_price))
    if promo.discount_type == "amount":
        return max(0, min(promo.discount_value, unit_price))
    return 0


def floor_tax(base: int, rate: Decimal) -> int:
    return int((Decimal(base) * rate).to_integral_value(ROUND_FLOOR))


def compute_quote(
    items: list[tuple[str, int]],
    products: dict[str, ProductInfo],
    rates: dict[str, Decimal],
    promotions: list[PromotionInfo],
    member_id: str | None,
) -> Quote:
    """DB に依存しない純粋な計算。items は (商品コード, 数量) の並び。"""
    is_member = member_id is not None
    best: dict[str, int] = {}
    for p in promotions if is_member else []:  # 会員でなければ値引きなし
        prod = products.get(p.product_code)
        if prod is None:
            continue
        best[p.product_code] = max(best.get(p.product_code, 0), unit_discount(prod.unit_price, p))

    lines: list[PriceLine] = []
    taxable = {"reduced": 0, "standard": 0}
    total_ex_tax = 0
    total_discount = 0
    for code, qty in items:
        prod = products[code]
        rate = rates[prod.tax_class]
        gross = prod.unit_price * qty
        discount = best.get(code, 0) * qty
        subtotal = gross - discount
        total_ex_tax += gross
        total_discount += discount
        taxable[prod.tax_class] += subtotal
        lines.append(
            PriceLine(
                product_code=code,
                name=prod.name,
                unit_price=prod.unit_price,
                quantity=qty,
                discount_amount=discount,
                tax_class=prod.tax_class,  # type: ignore[arg-type]
                applied_rate=float(rate),
                subtotal=subtotal,
            )
        )

    tax = {cls: (floor_tax(base, rates[cls]) if cls in rates else 0) for cls, base in taxable.items()}
    total_in_tax = sum(taxable.values()) + sum(tax.values())
    return Quote(
        member_id=member_id,
        lines=lines,
        total_ex_tax=total_ex_tax,
        total_discount=total_discount,
        taxable_by_class=TaxByClass(**taxable),
        tax_by_class=TaxByClass(**tax),
        total_in_tax=total_in_tax,
    )


def merge_items(items: list[CartItemIn]) -> list[tuple[str, int]]:
    """同じ商品コードが複数行で来ても1行にまとめる（順序は初出順）。"""
    merged: dict[str, int] = {}
    for it in items:
        merged[it.product_code] = merged.get(it.product_code, 0) + it.quantity
    for code, qty in merged.items():
        if qty > 99:
            raise ApiError(400, "VALIDATION_ERROR", "数量は1〜99で指定してください", [{"product_code": code}])
    return list(merged.items())


class PricingService:
    def __init__(self, db: Session):
        self.products = ProductRepository(db)
        self.members = MemberRepository(db)
        self.tax_rates = TaxRateRepository(db)
        self.promotions = PromotionRepository(db)

    def load_rates(self) -> dict:
        return self.tax_rates.current_rates(business_date())

    def quote(self, member_id: str | None, items: list[CartItemIn]) -> tuple[Quote, dict]:
        """見積りを返す。戻り値の2つ目は区分→TaxRate（確定時のスナップショット用）。"""
        merged = merge_items(items)
        codes = [c for c, _ in merged]
        found = self.products.find_many(codes)
        missing = [c for c in codes if c not in found]
        if missing:
            raise ApiError(404, "PRODUCT_NOT_FOUND", "商品がマスタ未登録です", [{"product_code": c} for c in missing])

        # 会員IDが指定されたら必ず存在を確認する。存在しない会員IDでは計算・会計させない
        # （会員なしで会計する場合は member_id を null にする）
        if member_id is not None and self.members.find(member_id) is None:
            raise ApiError(404, "MEMBER_NOT_FOUND", "会員が見つかりません。会員IDを確認してください")

        rate_rows = self.load_rates()
        products = {
            c: ProductInfo(p.product_code, p.name, p.unit_price_ex_tax, p.tax_class) for c, p in found.items()
        }
        for p in products.values():
            if p.tax_class not in rate_rows:
                raise ApiError(500, "TAX_RATE_NOT_FOUND", "税率が設定されていません")
        promos = [
            PromotionInfo(p.product_code, p.discount_type, p.discount_value)
            for p in self.promotions.active_for(codes, business_date())
        ]
        rates = {cls: Decimal(r.rate) for cls, r in rate_rows.items()}
        return compute_quote(merged, products, rates, promos, member_id), rate_rows
