# 簡易POSアプリ改（Lv2）

レジ担当者向けの会計（POS）アプリです。要件定義書（Lv2）・仕様設計書（Lv2 v1.3）・テスト仕様書（POS-TD-01）に沿って実装しています。画面はデザイン案E（ノルディック・ミニマル）です。

```
ブラウザ ──> Next.js（画面＋BFF: Route Handlers）──> FastAPI ──> MySQL
              JWT は HttpOnly Cookie で BFF が保持      （内部ネットワーク）
```

| フォルダ | 中身 |
|---|---|
| `api/` | FastAPI（認証・会員/商品照会・価格計算・取引確定）、SQLAlchemy、Alembic、seed、pytest |
| `web/` | Next.js 16（App Router）。ログイン画面・レジ画面、BFF、jest |
| `docker-compose.yml` | MySQL＋API＋Web をまとめて起動 |
| `.github/workflows/ci.yml` | pytest（MySQL）・jest・型チェック・ビルド・脆弱性チェック |

---

## 0. VS Code で起動する（Windows・いちばん簡単）

MySQL や Docker は不要です（ローカルではファイル型の SQLite を使います）。

1. 事前に入れておくもの：**Python 3.12**（<https://www.python.org/downloads/>、インストール時に「Add python.exe to PATH」にチェック）と **Node.js 22 LTS**（<https://nodejs.org/>）
2. VS Code で「ファイル → フォルダーを開く」から、この `pos-app` フォルダを開く
3. メニュー「ターミナル → 新しいターミナル」を開き、次を実行（初回のみ・数分かかります）
   ```powershell
   .\setup.bat
   ```
   「セットアップが終わりました」と出れば完了
4. 起動する
   ```powershell
   .\start.bat
   ```
   API と Web の黒いウィンドウが2つ開き、10秒ほどでブラウザに <http://localhost:3000/login> が開きます
5. 担当ID `S001` / パスワード `s001-password-2026` でログイン

止めるときは、2つの黒いウィンドウを閉じます。初期データに戻したいときは `.\reset-data.bat`（取引履歴も消えます）。

### VS Code のタスク・デバッグを使いたい場合（任意）

`vscode-sample` フォルダの名前を `.vscode` に変えると、次が使えるようになります。

- `Ctrl+Shift+B`：API と Web を VS Code のターミナル内で起動（タスク「POS: すべて起動」）
- 「実行とデバッグ」→「POS: すべて起動（デバッグ）」→ F5：ブレークポイントを使ったデバッグ
- タスク「POS: セットアップ（初回のみ）」「POS: 初期データを入れ直す」「POS: テスト（API）／テスト（Web）」

## 1. すぐに動かす（Docker）

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python seed.py
```

<http://localhost:3000> を開いて、下の担当者でログインします。

## 1-2. Azure Database for MySQL を使う

1. Azure ポータルでサーバーの「ネットワーク」に自分のPCのIPを追加し、「データベース」でデータベースを作る（例：`pos`）
2. `api/.env` を次のようにする（パスワードの記号は URL エンコード。例：`@`→`%40`）
   ```
   DATABASE_URL=mysql+pymysql://<ユーザー名>:<パスワード>@<サーバー名>.mysql.database.azure.com:3306/<データベース名>?charset=utf8mb4
   DB_SSL=true
   ```
3. `api` フォルダで `.venv\Scripts\python.exe -m alembic upgrade head` → `.venv\Scripts\python.exe seed.py` → API を起動

注意：`seed.py` はそのデータベースの中身を消して入れ直します。`pytest` は既定で SQLite を使うので Azure には触れません（`TEST_DATABASE_URL` に Azure を指定しないこと）。

## 2. Docker を使わずに動かす

前提：Python 3.11 以上、Node.js 22、MySQL 8。

```bash
# MySQL にデータベースとユーザーを作る
mysql -uroot -e "CREATE DATABASE pos CHARACTER SET utf8mb4;
  CREATE USER 'pos'@'localhost' IDENTIFIED BY 'pos-local-password';
  GRANT ALL ON pos.* TO 'pos'@'localhost';"

# API
cd api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env            # JWT_SECRET などを必要に応じて変更
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8000

# Web（別のターミナル）
cd web
npm install
cp .env.example .env.local
npm run dev
```

<http://localhost:3000> を開きます。API の Swagger は開発時のみ <http://localhost:8000/docs> で見られます（`APP_ENV=prod` では無効）。

MySQL がなくても、`api/.env` の `DATABASE_URL` を `sqlite:///./pos.db` にすれば動きます。

## 3. 初期データ（すべて架空）

| 種類 | 値 |
|---|---|
| 担当者 | `S001` / `s001-password-2026`（山田 太郎）、`S002` / `s002-password-2026`（鈴木 次郎） |
| 会員 | `M0001` テスト太郎、`M0002` テスト花子、`M0003` サンプル三郎（`M9999` は存在しない会員） |
| 商品 | 30点。例：`4901234567894` おにぎり 鮭（8%）、`4901234567900` 緑茶 500ml（8%）、`4909999999999` ボールペン 黒（10%）、`4909999999900` ティッシュ 5箱（10%） |
| 値引き企画 | 常時有効（〜2027年末・会員限定）：緑茶 20円引き、ティッシュ 10%引き。テスト用（2026年9月のみ）：おにぎり 10%引き、対象商品300 500円引きなど |
| 税率 | 標準 10% / 軽減 8%（`tax_rate` テーブルで変更可能） |

## 4. 使い方（レジ画面）

1. 会員カードの ID を入力して「読込」。存在しない会員IDはエラーになり、会員として会計できません（会員カードがないお客様は、何も入力せずに「会員なし」で会計できます）
2. 「カメラを起動」してバーコードを枠に映す、または商品コード13桁を入力して Enter／「追加」
   - USB やBluetoothのバーコードリーダー（キーボードとして動くもの）も、商品コード欄にフォーカスを置けばそのまま使えます
3. 商品を押すと選択され、数量の −／＋ と「削除」が出ます（数量は1〜99）
4. 右側の税込合計を確認して「購入する」→ 完了画面 →「次の会計へ」

カメラは `localhost` か HTTPS のページでしか使えません。スマホ実機で試すときは HTTPS で公開してください。

## 5. テスト

```bash
# バックエンド（UT-BE-01〜11、IT-*、ST-SEC-01〜05、ST-NFR-01。ロック関連はロックしないことを確認するテストに変更）
cd api && pytest
# MySQL で結合テストをする場合
TEST_DATABASE_URL='mysql+pymysql://pos:pos-local-password@localhost:3306/pos_test?charset=utf8mb4' pytest

# フロントエンド（UT-FE-01〜08）
cd web && npm test
```

テスト基準日は 2026-09-05 に固定しています（`BUSINESS_DATE`）。

| テスト仕様書のID | 実装 |
|---|---|
| UT-BE-01〜11 | `api/tests/test_unit_backend.py` |
| IT-AUTH / MEMBER / PRODUCT / PRICE / TX / TAX | `api/tests/test_integration.py` |
| ST-SEC-01〜05、ST-NFR-01 | `api/tests/test_integration.py`（`test_st_*`） |
| UT-FE-01〜03 | `web/__tests__/cartStore.test.ts` |
| UT-FE-04 | `web/__tests__/format.test.ts` |
| UT-FE-05〜08 | `web/__tests__/components.test.tsx` |
| AT-01〜10 | 手動（ブラウザ操作） |

## 6. 仕様書から実装で決めたこと

仕様書に書かれていない点や、解釈が必要だった点です。変更したい場合はここを見直してください。

- **ログイン失敗時のロックはしない**：何回失敗しても 401 を返すだけで、ロックアウトはしない（要件定義書 NFR-010、テスト仕様書 ST-FR001-03・IT-AUTH-03・UT-BE-10 とは異なる）。`staff` テーブルに `failed_count`・`locked_until` 列は持たない
- **商品照会の入力形式**：`GET /api/products/{code}` は読み取ったバーコードをそのまま照会できるよう英数字20文字まで受け付け、マスタに無ければ 404（`P-UNREG` もここで404になる）。価格計算と取引確定の商品コードは数字13桁のみ
- **値引き**：1個あたりの値引き（割合は切り捨て、金額は単価で頭打ち）× 数量。同じ商品に複数の企画があるときは値引きが最も大きい1件を使う。`members_only=false` の企画は会員でなくても適用
- **存在しない会員ID**：会員照会・価格計算・取引確定のすべてで 404 `MEMBER_NOT_FOUND` を返し、会計できない。会員なしで会計するときは `member_id` を `null` にする（画面では会員IDを入力しない）
- **422（金額不一致）**：取引は保存せず、レスポンスの `data` にサーバ再計算値を入れて返す。画面はその値でカートを同期し、「もう一度購入する」を案内する
- **追加したAPI**：`GET /api/auth/me`（ヘッダーに担当者名を出すため）、`POST /api/auth/logout`
- **税率の変更**：`tax_rate` に新しい行（`valid_from` 付き）を追加すると、その日以降の会計に使われる。過去の取引は明細の `applied_rate` のまま変わらない

## 7. 本番（Azure）に向けて

- Web：Azure Static Web Apps（または App Service）。環境変数 `API_BASE_URL`（内部のAPI URL）、`COOKIE_SECURE=true`
- API：Azure Container Apps（最小レプリカ1以上）。`APP_ENV=prod`、`DATABASE_URL`、`CORS_ORIGINS`（本番URLのみ）、`JWT_SECRET`（長いランダム値）
- DB：Azure Database for MySQL。`alembic upgrade head` → `python seed.py`
- `APP_ENV=prod` で `/docs` `/redoc` `/openapi.json` が 404 になることを確認する
