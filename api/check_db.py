"""DB 接続チェック。api フォルダで実行:  .venv\\Scripts\\python.exe check_db.py"""
import sys

from sqlalchemy import inspect, text

from app.config import get_settings

s = get_settings()
url = s.DATABASE_URL
safe = url.split("@")[-1] if "@" in url else url
print(f"接続先: {safe}  (SSL: {s.DB_SSL})")

try:
    from app.db import engine

    with engine.connect() as c:
        c.execute(text("SELECT 1"))
    print("OK  DB に接続できました")
except Exception as e:  # noqa: BLE001
    msg = str(e)
    print("NG  DB に接続できません")
    hints = {
        "2003": "サーバーに届いていません。Azure ポータル →「ネットワーク」で自分のPCのIPをファイアウォール規則に追加してください。",
        "1045": "ユーザー名かパスワードが違います。パスワードの記号は URL エンコードが必要です（% → %25、& → %26、@ → %40、# → %23）。",
        "1049": "データベースがありません。Azure ポータル →「データベース」で作るか、.env の最後の /pos を実在する名前にしてください。",
        "3159": "SSL が必要です。.env に DB_SSL=true を書いてください。",
        "CERTIFICATE_VERIFY_FAILED": "SSL 証明書を検証できません。README の Azure の章を参照するか、この画面を共有してください。",
    }
    for k, v in hints.items():
        if k in msg:
            print("  → " + v)
            break
    print("  詳細:", msg.splitlines()[0][:300])
    sys.exit(1)

tables = set(inspect(engine).get_table_names())
need = {"staff", "member", "product", "tax_rate", "promotion", "transaction", "transaction_detail"}
missing = need - tables
if missing:
    print("NG  テーブルがありません:", ", ".join(sorted(missing)))
    print("  → .venv\\Scripts\\python.exe -m alembic upgrade head  を実行してください")
    sys.exit(1)
print("OK  テーブルがそろっています")

with engine.connect() as c:
    n = c.execute(text("SELECT COUNT(*) FROM staff")).scalar()
if not n:
    print("NG  担当者データがありません → .venv\\Scripts\\python.exe seed.py を実行してください")
    sys.exit(1)
print(f"OK  担当者 {n} 人。ログインできる状態です")
