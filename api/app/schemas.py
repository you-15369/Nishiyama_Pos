"""入出力スキーマ（Pydantic）。型・桁・範囲をここで検証する（NFR-013）。"""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

ProductCode = Annotated[str, Field(pattern=r"^\d{13}$", description="商品コード（JAN13桁）")]
MemberId = Annotated[str, Field(pattern=r"^[A-Za-z0-9\-]{1,20}$", description="会員ID（20文字以内）")]
Quantity = Annotated[int, Field(ge=1, le=99)]
TaxClass = Literal["standard", "reduced"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- 認証 ----
class LoginRequest(StrictModel):
    login_id: Annotated[str, Field(min_length=1, max_length=20)]
    password: Annotated[str, Field(min_length=1, max_length=128)]


class StaffOut(BaseModel):
    staff_id: int
    login_id: str
    name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    staff: StaffOut


# ---- 会員・商品・税率 ----
class MemberOut(BaseModel):
    """電話番号・住所などは返さない（NFR-016）。"""

    member_id: str
    name: str


class ProductOut(BaseModel):
    product_code: str
    name: str
    unit_price: int
    tax_class: TaxClass


class TaxRateOut(BaseModel):
    tax_class: TaxClass
    rate: float
    valid_from: str


# ---- 価格計算 ----
class CartItemIn(StrictModel):
    product_code: ProductCode
    quantity: Quantity


class PriceRequest(StrictModel):
    member_id: MemberId | None = None
    items: Annotated[list[CartItemIn], Field(min_length=1, max_length=200)]


class PriceLine(BaseModel):
    product_code: str
    name: str
    unit_price: int
    quantity: int
    discount_amount: int
    tax_class: TaxClass
    applied_rate: float
    subtotal: int  # 値引き後・税抜


class TaxByClass(BaseModel):
    reduced: int = 0
    standard: int = 0


class Quote(BaseModel):
    member_id: str | None
    lines: list[PriceLine]
    total_ex_tax: int  # 値引き前の税抜合計
    total_discount: int
    taxable_by_class: TaxByClass  # 値引き後の課税対象額
    tax_by_class: TaxByClass
    total_in_tax: int


class TransactionRequest(PriceRequest):
    client_total_in_tax: Annotated[int, Field(ge=0)]


class TransactionOut(BaseModel):
    transaction_id: int
    total_ex_tax: int
    total_discount: int
    total_in_tax: int
    tax_by_class: TaxByClass
    transacted_at: datetime
