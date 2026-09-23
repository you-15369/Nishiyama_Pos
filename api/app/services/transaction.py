"""TransactionService：サーバで再計算 → フロント合計と照合 → 一致時のみ保存（FR-009, FR-010, NFR-012）。"""
from decimal import Decimal

from sqlalchemy.orm import Session

from ..errors import ApiError
from ..models import Transaction, TransactionDetail
from ..repositories import now_jst_naive
from ..schemas import Quote, TransactionOut, TransactionRequest
from .pricing import PricingService


class TotalMismatchError(ApiError):
    def __init__(self, server_quote: Quote):
        super().__init__(
            422,
            "TOTAL_MISMATCH",
            "金額を更新しました。最新の金額で購入してください",
            data=server_quote.model_dump(mode="json"),
        )
        self.server_quote = server_quote


def verify_total(client_total: int, quote: Quote) -> None:
    if client_total != quote.total_in_tax:
        raise TotalMismatchError(quote)


class TransactionService:
    def __init__(self, db: Session):
        self.db = db
        self.pricing = PricingService(db)

    def confirm(self, staff_id: int, req: TransactionRequest) -> TransactionOut:
        quote, rate_rows = self.pricing.quote(req.member_id, req.items)
        verify_total(req.client_total_in_tax, quote)

        tx = Transaction(
            transacted_at=now_jst_naive(),
            staff_id=staff_id,
            member_id=quote.member_id,
            total_ex_tax=quote.total_ex_tax,
            total_discount=quote.total_discount,
            total_in_tax=quote.total_in_tax,
        )
        try:
            self.db.add(tx)
            self.db.flush()
            for line in quote.lines:
                self.db.add(
                    TransactionDetail(
                        transaction_id=tx.transaction_id,
                        product_code=line.product_code,
                        product_name=line.name,
                        unit_price=line.unit_price,
                        quantity=line.quantity,
                        discount_amount=line.discount_amount,
                        tax_class=line.tax_class,
                        applied_rate=Decimal(rate_rows[line.tax_class].rate),
                    )
                )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return TransactionOut(
            transaction_id=tx.transaction_id,
            total_ex_tax=quote.total_ex_tax,
            total_discount=quote.total_discount,
            total_in_tax=quote.total_in_tax,
            tax_by_class=quote.tax_by_class,
            transacted_at=tx.transacted_at,
        )
