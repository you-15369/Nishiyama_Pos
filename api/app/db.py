"""DB接続。常時稼働でコネクションプールを維持する（NFR-005）。"""
import ssl
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    s = get_settings()
    url = s.DATABASE_URL
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    connect_args = {}
    if s.DB_SSL:
        # サーバ証明書を検証したうえで暗号化する（Azure の証明書は OS の証明書ストアで検証できる）
        ctx = ssl.create_default_context(cafile=s.DB_SSL_CA or None)
        connect_args["ssl"] = ctx
    return create_engine(
        url, connect_args=connect_args, pool_pre_ping=True, pool_size=5, max_overflow=10, pool_recycle=1800
    )


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
