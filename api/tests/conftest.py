"""テスト共通設定。

- 既定は SQLite（ファイル）で実行する。Docker MySQL で結合テストをする場合は
  TEST_DATABASE_URL=mysql+pymysql://pos:pos@127.0.0.1:3306/pos_test を指定する。
- テスト基準日は 2026-09-05 に固定（テスト仕様書 §1.3）。
"""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ["BUSINESS_DATE"] = "2026-09-05"
os.environ["APP_ENV"] = "dev"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["JWT_SECRET"] = "test-secret-for-pytest-only-32bytes!!"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from seed import seed  # noqa: E402

S001 = ("S001", "s001-password-2026")
S002 = ("S002", "s002-password-2026")


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _seeded():
    with SessionLocal() as db:
        seed(db)
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth(client):
    res = client.post("/api/auth/login", json={"login_id": S001[0], "password": S001[1]})
    assert res.status_code == 200
    client.cookies.clear()  # Cookie ではなくヘッダで明示的に渡す
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
