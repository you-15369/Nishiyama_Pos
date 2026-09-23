"""単体テスト UT-BE-01〜11（テスト仕様書 §5.1）。"""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import Transaction, TransactionDetail
from app.repositories import MemberRepository
from app.schemas import CartItemIn, TransactionRequest
from app.security import PasswordPolicyError, hash_password, verify_password
from app.services.auth import AuthService
from app.errors import ApiError
from app.services.pricing import ProductInfo, PromotionInfo, compute_quote
from app.services.transaction import TotalMismatchError, TransactionService, verify_total

RATES = {"reduced": Decimal("0.080"), "standard": Decimal("0.100")}
ONIGIRI = ProductInfo("4901234567894", "おにぎり", 150, "reduced")
OCHA = ProductInfo("4901234567895", "お茶", 130, "reduced")
PEN = ProductInfo("4909999999999", "ボールペン", 200, "standard")
P300 = ProductInfo("4900000000300", "対象商品300", 300, "standard")
PRODUCTS = {p.product_code: p for p in (ONIGIRI, OCHA, PEN, P300)}
PROMO_ONIGIRI_10 = PromotionInfo(ONIGIRI.product_code, "rate", 10)
PROMO_300_500 = PromotionInfo(P300.product_code, "amount", 500)


def test_quote_mixed_tax():  # UT-BE-01
    q = compute_quote([(ONIGIRI.product_code, 2), (PEN.product_code, 1)], PRODUCTS, RATES, [], None)
    assert q.total_ex_tax == 500
    assert q.total_discount == 0
    assert q.tax_by_class.reduced == 24
    assert q.tax_by_class.standard == 20
    assert q.total_in_tax == 544


def test_tax_floor():  # UT-BE-02
    q = compute_quote([(OCHA.product_code, 1)], PRODUCTS, RATES, [], None)
    assert q.tax_by_class.reduced == 10  # 10.4 → floor 10（四捨五入なら 10、切り上げなら 11）
    assert q.total_in_tax == 140


def test_member_discount():  # UT-BE-03
    member = compute_quote([(ONIGIRI.product_code, 2)], PRODUCTS, RATES, [PROMO_ONIGIRI_10], "M0001")
    assert member.total_discount == 30
    assert member.lines[0].subtotal == 270
    assert member.tax_by_class.reduced == 21
    assert member.total_in_tax == 291

    guest = compute_quote([(ONIGIRI.product_code, 2)], PRODUCTS, RATES, [PROMO_ONIGIRI_10], None)
    assert guest.total_discount == 0
    assert guest.tax_by_class.reduced == 24
    assert guest.total_in_tax == 324


def test_discount_not_negative():  # UT-BE-04
    q = compute_quote([(P300.product_code, 1)], PRODUCTS, RATES, [PROMO_300_500], "M0001")
    assert q.total_discount == 300
    assert q.lines[0].subtotal == 0
    assert q.tax_by_class.standard == 0
    assert q.total_in_tax == 0


def test_confirm_total_mismatch():  # UT-BE-05
    q = compute_quote([(OCHA.product_code, 1)], PRODUCTS, RATES, [], None)
    verify_total(140, q)
    with pytest.raises(TotalMismatchError) as e:
        verify_total(139, q)
    assert e.value.status == 422
    assert e.value.data["total_in_tax"] == 140


def test_snapshot_persists(db):  # UT-BE-06
    req = TransactionRequest(
        member_id="M0001",
        items=[CartItemIn(product_code=ONIGIRI.product_code, quantity=2)],
        client_total_in_tax=291,
    )
    staff = AuthService(db).staff.find_by_login_id("S001")
    out = TransactionService(db).confirm(staff.staff_id, req)
    detail = db.query(TransactionDetail).filter_by(transaction_id=out.transaction_id).one()
    assert detail.product_name == "おにぎり 鮭"
    assert detail.unit_price == 150
    assert detail.discount_amount == 30
    assert detail.tax_class == "reduced"
    assert Decimal(detail.applied_rate) == Decimal("0.080")


@pytest.mark.parametrize("qty,ok", [(0, False), (1, True), (99, True), (100, False)])
def test_quantity_bounds(qty, ok):  # UT-BE-07
    if ok:
        assert CartItemIn(product_code="4901234567894", quantity=qty).quantity == qty
    else:
        with pytest.raises(ValidationError):
            CartItemIn(product_code="4901234567894", quantity=qty)


@pytest.mark.parametrize("code", ["490123456789", "49012345678945", "49012345678AB", "' OR 1=1--", ""])
def test_product_code_format(code):  # UT-BE-08
    with pytest.raises(ValidationError):
        CartItemIn(product_code=code, quantity=1)


def test_password_verify():  # UT-BE-09
    h = hash_password("correct-horse-battery")
    assert h != "correct-horse-battery"  # 平文で保存しない
    assert verify_password("correct-horse-battery", h)
    assert not verify_password("wrong-horse-battery!", h)
    with pytest.raises(PasswordPolicyError):
        hash_password("short-pass-14c")  # 14文字は拒否（NFR-009）


def test_login_no_lockout(db):  # UT-BE-10（ロックアウトなし）
    svc = AuthService(db)
    for _ in range(12):
        with pytest.raises(ApiError) as e:
            svc.authenticate("S002", "wrong-password-xxxx")
        assert e.value.status == 401
    # 何回失敗しても、正しいパスワードならログインできる
    assert svc.authenticate("S002", "s002-password-2026").login_id == "S002"


def test_unknown_member_is_rejected(db):  # 存在しない会員IDでは計算させない
    from app.services.pricing import PricingService

    with pytest.raises(ApiError) as e:
        PricingService(db).quote("M9999", [CartItemIn(product_code=ONIGIRI.product_code, quantity=1)])
    assert e.value.status == 404 and e.value.code == "MEMBER_NOT_FOUND"


def test_find_member(db):  # UT-BE-11
    repo = MemberRepository(db)
    assert repo.find("M0001").name == "テスト太郎"
    assert repo.find("M9999") is None


def test_amount_discount_member_only():  # 金額値引きも会員に限る
    promo = PromotionInfo(PEN.product_code, "amount", 20)
    member = compute_quote([(PEN.product_code, 2)], PRODUCTS, RATES, [promo], "M0001")
    assert member.total_discount == 40 and member.lines[0].subtotal == 360
    guest = compute_quote([(PEN.product_code, 2)], PRODUCTS, RATES, [promo], None)
    assert guest.total_discount == 0 and guest.lines[0].subtotal == 400
