"""結合テスト IT-*（§4）と、ローカルで確認できるシステムテスト ST-SEC / ST-NFR（§3.2）。"""
from datetime import date

from fastapi.testclient import TestClient

from app.config import get_settings
from app.models import Product, Staff, TaxRate, Transaction, TransactionDetail

from .conftest import S001, S002

ONIGIRI = "4901234567894"
OCHA = "4901234567895"
PEN = "4909999999999"
P300 = "4900000000300"


def price(client, headers, items, member_id=None):
    return client.post("/api/cart/price", json={"member_id": member_id, "items": items}, headers=headers)


# ---------- 認証 ----------
def test_it_auth_01_login_ok(client):
    res = client.post("/api/auth/login", json={"login_id": S001[0], "password": S001[1]})
    assert res.status_code == 200
    assert res.json()["staff"]["login_id"] == "S001"
    set_cookie = res.headers["set-cookie"].lower()
    assert "pos_token=" in set_cookie and "httponly" in set_cookie


def test_it_auth_02_wrong_password(client):
    res = client.post("/api/auth/login", json={"login_id": "S002", "password": "wrong-password-xxxx"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"
    res = client.post("/api/auth/login", json={"login_id": "S999", "password": "wrong-password-xxxx"})
    assert res.status_code == 401  # 存在しないIDでも同じ応答


def test_it_auth_03_no_lockout(client):
    for _ in range(12):
        assert client.post("/api/auth/login", json={"login_id": "S002", "password": "wrong-password-xxxx"}).status_code == 401
    res = client.post("/api/auth/login", json={"login_id": S002[0], "password": S002[1]})
    assert res.status_code == 200


# ---------- 会員・商品 ----------
def test_it_member_01(client, auth):
    res = client.get("/api/members/M0001", headers=auth)
    assert res.status_code == 200
    assert res.json() == {"member_id": "M0001", "name": "テスト太郎"}  # 電話・住所は返さない


def test_it_member_02(client, auth):
    res = client.get("/api/members/M9999", headers=auth)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "MEMBER_NOT_FOUND"


def test_it_product_01(client, auth):
    res = client.get(f"/api/products/{ONIGIRI}", headers=auth)
    assert res.status_code == 200
    assert res.json() == {"product_code": ONIGIRI, "name": "おにぎり 鮭", "unit_price": 150, "tax_class": "reduced"}


def test_it_product_02(client, auth):
    res = client.get("/api/products/P-UNREG", headers=auth)
    assert res.status_code == 404
    assert res.json()["error"] == {"code": "PRODUCT_NOT_FOUND", "message": "商品がマスタ未登録です", "details": []}


# ---------- 価格計算 ----------
def test_it_price_01_member_mixed(client, auth):
    res = price(client, auth, [{"product_code": ONIGIRI, "quantity": 2}, {"product_code": PEN, "quantity": 1}], "M0001")
    assert res.status_code == 200
    d = res.json()["data"]
    assert d["total_ex_tax"] == 500
    assert d["total_discount"] == 30
    assert d["tax_by_class"] == {"reduced": 21, "standard": 20}  # 270×0.08=21.6→21, 200×0.1=20
    assert d["total_in_tax"] == 270 + 200 + 21 + 20


def test_it_price_02_quantity_bounds(client, auth):
    for qty, status in [(1, 200), (99, 200), (0, 400), (100, 400)]:
        assert price(client, auth, [{"product_code": ONIGIRI, "quantity": qty}]).status_code == status, qty


def test_it_price_03_no_member(client, auth):
    d = price(client, auth, [{"product_code": ONIGIRI, "quantity": 2}], None).json()["data"]
    assert d["total_discount"] == 0 and d["total_in_tax"] == 324


def test_it_price_04_discount_capped(client, auth):
    d = price(client, auth, [{"product_code": P300, "quantity": 1}], "M0001").json()["data"]
    assert d["lines"][0]["discount_amount"] == 300
    assert d["lines"][0]["subtotal"] == 0
    assert d["total_in_tax"] == 0


def test_price_unknown_member_is_rejected(client, auth):
    res = price(client, auth, [{"product_code": ONIGIRI, "quantity": 2}], "M9999")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "MEMBER_NOT_FOUND"


def test_price_unregistered_product(client, auth):
    res = price(client, auth, [{"product_code": "4999999999999", "quantity": 1}])
    assert res.status_code == 404


def test_price_promotion_period(client, auth):  # ST-FR007-03 期間外は値引きなし
    d = price(client, auth, [{"product_code": OCHA, "quantity": 1}], "M0001").json()["data"]
    assert d["total_discount"] == 0


def test_price_discount_is_member_only(client, auth):  # R-011 会員に限り値引き
    items = [{"product_code": "4901234567900", "quantity": 1}, {"product_code": "4909999999900", "quantity": 1}]
    guest = price(client, auth, items, None).json()["data"]
    assert guest["total_discount"] == 0
    member = price(client, auth, items, "M0001").json()["data"]
    # 緑茶 20円引き（金額）＋ ティッシュ 398×10%=39.8→39（割合）
    assert member["total_discount"] == 20 + 39


# ---------- 取引確定 ----------
def _confirm(client, auth, total, member_id="M0001"):
    return client.post(
        "/api/transactions",
        json={"member_id": member_id, "items": [{"product_code": ONIGIRI, "quantity": 2}, {"product_code": PEN, "quantity": 1}], "client_total_in_tax": total},
        headers=auth,
    )


def test_it_tx_01_ok(client, auth, db):
    res = _confirm(client, auth, 511)
    assert res.status_code == 201
    tx_id = res.json()["data"]["transaction_id"]
    tx = db.get(Transaction, tx_id)
    assert tx.member_id == "M0001" and tx.total_in_tax == 511 and tx.total_discount == 30
    assert db.get(Staff, tx.staff_id).login_id == "S001"
    assert db.query(TransactionDetail).filter_by(transaction_id=tx_id).count() == 2


def test_it_tx_02_tampered_total(client, auth, db):
    res = _confirm(client, auth, 1)
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "TOTAL_MISMATCH"
    assert body["data"]["total_in_tax"] == 511  # サーバ再計算値を同梱
    assert db.query(Transaction).count() == 0


def test_tx_unknown_member_is_rejected(client, auth, db):
    res = _confirm(client, auth, 544, member_id="M9999")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "MEMBER_NOT_FOUND"
    assert db.query(Transaction).count() == 0


def test_tx_without_member_is_ok(client, auth, db):  # 会員なし（member_id=null）は会計できる
    res = _confirm(client, auth, 544, member_id=None)
    assert res.status_code == 201
    assert db.get(Transaction, res.json()["data"]["transaction_id"]).member_id is None


def test_it_tx_03_snapshot_immutable(client, auth, db):
    tx_id = _confirm(client, auth, 511).json()["data"]["transaction_id"]
    db.get(Product, ONIGIRI).unit_price_ex_tax = 999
    db.commit()
    db.expire_all()
    tx = db.get(Transaction, tx_id)
    assert tx.total_in_tax == 511
    detail = db.query(TransactionDetail).filter_by(transaction_id=tx_id, product_code=ONIGIRI).one()
    assert detail.unit_price == 150


def test_it_tax_01(client, auth):
    d = client.get("/api/tax-rates", headers=auth).json()["data"]
    assert {r["tax_class"]: r["rate"] for r in d} == {"reduced": 0.08, "standard": 0.1}


def test_it_tax_02_rate_change(client, auth, db):
    old_id = _confirm(client, auth, 511).json()["data"]["transaction_id"]
    db.add(TaxRate(tax_class="reduced", rate="0.050", valid_from=date(2026, 9, 1)))
    db.commit()
    # 270×0.05=13.5→13 / 200×0.1=20 → 270+200+13+20=503
    res = _confirm(client, auth, 503)
    assert res.status_code == 201
    new = db.query(TransactionDetail).filter_by(transaction_id=res.json()["data"]["transaction_id"], product_code=ONIGIRI).one()
    old = db.query(TransactionDetail).filter_by(transaction_id=old_id, product_code=ONIGIRI).one()
    assert float(new.applied_rate) == 0.05 and float(old.applied_rate) == 0.08
    assert db.get(Transaction, old_id).total_in_tax == 511


# ---------- セキュリティ（ST-SEC） ----------
def test_st_sec_01_unauthenticated(client):
    for method, url in [("get", "/api/members/M0001"), ("get", f"/api/products/{ONIGIRI}"), ("get", "/api/tax-rates")]:
        assert getattr(client, method)(url).status_code == 401
    assert client.post("/api/cart/price", json={"items": [{"product_code": ONIGIRI, "quantity": 1}]}).status_code == 401
    assert client.post("/api/transactions", json={"items": [], "client_total_in_tax": 0}).status_code in (400, 401)


def test_st_sec_01_tampered_token(client, auth):
    bad = {"Authorization": auth["Authorization"][:-3] + "abc"}
    assert client.get("/api/tax-rates", headers=bad).status_code == 401


def test_st_sec_03_sql_injection(client, auth, db):
    assert client.get("/api/products/' OR 1=1--", headers=auth).status_code in (400, 404)
    res = price(client, auth, [{"product_code": "' OR 1=1--", "quantity": 1}])
    assert res.status_code == 400
    assert client.get("/api/members/M0001' OR '1'='1", headers=auth).status_code in (400, 404)
    assert db.query(Product).count() == 30


def test_st_sec_04_docs_disabled_in_prod(monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("APP_ENV", "prod")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as c:
            for path in ("/docs", "/redoc", "/openapi.json"):
                assert c.get(path).status_code == 404
    finally:
        get_settings.cache_clear()


def test_docs_enabled_in_dev(client):
    assert client.get("/docs").status_code == 200


def test_st_sec_05_cors(client):
    ok = client.options("/api/tax-rates", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    ng = client.options("/api/tax-rates", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in ng.headers


def test_st_nfr_01_password_hashed(db):
    s = db.query(Staff).filter_by(login_id="S001").one()
    assert s.password_hash.startswith("$2") and "s001-password" not in s.password_hash
