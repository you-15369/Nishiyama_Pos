"""架空の初期データを投入する（仕様設計書 §5.3 / テスト仕様書 §1.3）。

使い方:
    python seed.py            # 既存データを消して入れ直す
実在の個人情報は使わない（NFR-016）。
"""
from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Member, Product, Promotion, Staff, TaxRate, Transaction, TransactionDetail
from app.security import hash_password

# 担当者（パスワードは15文字以上。README に記載）
STAFF = [
    ("S001", "山田 太郎", "s001-password-2026"),
    ("S002", "鈴木 次郎", "s002-password-2026"),
]

MEMBERS = [
    ("M0001", "テスト太郎", "000-0000-0001", "架空県架空市1-1", "男性", 35),
    ("M0002", "テスト花子", "000-0000-0002", "架空県架空市2-2", "女性", 28),
    ("M0003", "サンプル三郎", "000-0000-0003", "架空県架空町3-3", "男性", 61),
]

# (商品コード, 商品名, 税抜単価, 税率区分)
PRODUCTS = [
    # テスト仕様書の代表商品
    ("4901234567894", "おにぎり 鮭", 150, "reduced"),
    ("4901234567895", "お茶", 130, "reduced"),
    ("4909999999999", "ボールペン 黒", 200, "standard"),
    ("4900000000300", "対象商品300", 300, "standard"),
    # その他（食品＝軽減8%、それ以外＝標準10%）
    ("4901234567900", "緑茶 500ml", 120, "reduced"),
    ("4901234567901", "ミネラルウォーター 2L", 98, "reduced"),
    ("4901234567902", "サンドイッチ ミックス", 298, "reduced"),
    ("4901234567903", "食パン 6枚切", 168, "reduced"),
    ("4901234567904", "牛乳 1000ml", 218, "reduced"),
    ("4901234567905", "ヨーグルト プレーン", 158, "reduced"),
    ("4901234567906", "バナナ 1房", 178, "reduced"),
    ("4901234567907", "カップ麺 しょうゆ", 138, "reduced"),
    ("4901234567908", "チョコレート", 108, "reduced"),
    ("4901234567909", "ポテトチップス うすしお", 128, "reduced"),
    ("4901234567910", "缶コーヒー 微糖", 115, "reduced"),
    ("4901234567911", "からあげ弁当", 480, "reduced"),
    ("4901234567912", "サラダ チキン", 238, "reduced"),
    ("4901234567913", "卵 10個入", 248, "reduced"),
    ("4901234567914", "アイスクリーム バニラ", 140, "reduced"),
    ("4901234567915", "オレンジジュース 1L", 198, "reduced"),
    ("4909999999900", "ティッシュ 5箱", 398, "standard"),
    ("4909999999901", "トイレットペーパー 12ロール", 458, "standard"),
    ("4909999999902", "ハンドソープ 詰替", 248, "standard"),
    ("4909999999903", "歯ブラシ", 198, "standard"),
    ("4909999999904", "ノート A5", 150, "standard"),
    ("4909999999905", "乾電池 単3 4本", 398, "standard"),
    ("4909999999906", "ゴミ袋 45L 20枚", 228, "standard"),
    ("4909999999907", "マスク 30枚", 498, "standard"),
    ("4909999999908", "ビニール傘", 550, "standard"),
    ("4909999999909", "マスキングテープ", 180, "standard"),
]

TAX_RATES = [
    ("standard", "0.100", date(2019, 10, 1)),
    ("reduced", "0.080", date(2019, 10, 1)),
]

# (対象商品, 種別, 値, 開始, 終了, 会員限定)
PROMOTIONS = [
    # テスト仕様書の代表企画（基準日 2026-09-05 に有効）
    ("4901234567894", "rate", 10, date(2026, 9, 1), date(2026, 9, 30), True),
    ("4900000000300", "amount", 500, date(2026, 9, 1), date(2026, 9, 30), True),
    # 期間外の企画（適用されない）
    ("4901234567895", "amount", 20, date(2026, 8, 1), date(2026, 8, 31), True),
    # 会員限定でない企画（会員なしでも適用）
    ("4901234567908", "amount", 10, date(2026, 9, 1), date(2026, 9, 30), False),
    # デモ用の長期企画（会員限定）
    ("4901234567900", "amount", 20, date(2026, 1, 1), date(2027, 12, 31), True),
    ("4909999999900", "rate", 10, date(2026, 1, 1), date(2027, 12, 31), True),
]


def seed(db: Session) -> None:
    for model in (TransactionDetail, Transaction, Promotion, Product, TaxRate, Member, Staff):
        db.execute(delete(model))
    db.flush()

    for login_id, name, pw in STAFF:
        db.add(Staff(login_id=login_id, name=name, password_hash=hash_password(pw)))
    for mid, name, phone, addr, gender, age in MEMBERS:
        db.add(Member(member_id=mid, name=name, phone=phone, address=addr, gender=gender, age=age))
    for cls, rate, since in TAX_RATES:
        db.add(TaxRate(tax_class=cls, rate=rate, valid_from=since))
    for code, name, price, cls in PRODUCTS:
        db.add(Product(product_code=code, name=name, unit_price_ex_tax=price, tax_class=cls))
    db.flush()
    for code, typ, val, start, end, members_only in PROMOTIONS:
        db.add(
            Promotion(
                product_code=code,
                discount_type=typ,
                discount_value=val,
                start_date=start,
                end_date=end,
                members_only=members_only,
            )
        )
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
    print(f"seeded: staff={len(STAFF)} members={len(MEMBERS)} products={len(PRODUCTS)} promotions={len(PROMOTIONS)}")
