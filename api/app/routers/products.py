"""GET /api/products/{product_code}（FR-003, FR-005）。"""
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_staff
from ..errors import ApiError
from ..repositories import ProductRepository
from ..schemas import ProductOut

router = APIRouter(prefix="/api/products", tags=["products"], dependencies=[Depends(current_staff)])


@router.get("/{product_code}", response_model=ProductOut)
def get_product(
    # 読み取ったバーコードをそのまま照会するため、ここでは英数字20文字まで受け付ける。
    # マスタに無ければ 404（13桁でない社内コード等も「未登録」として扱う）
    product_code: Annotated[str, Path(pattern=r"^[A-Za-z0-9\-]{1,20}$")],
    db: Session = Depends(get_db),
):
    p = ProductRepository(db).find(product_code)
    if p is None:
        raise ApiError(404, "PRODUCT_NOT_FOUND", "商品がマスタ未登録です")
    return ProductOut(product_code=p.product_code, name=p.name, unit_price=p.unit_price_ex_tax, tax_class=p.tax_class)
