"""アプリ設定（環境変数から読み込む）。秘密情報はコードに書かない（NFR-014）。"""
from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "dev"  # dev / prod
    DATABASE_URL: str = "sqlite:///./pos.db"
    # MySQL を SSL（暗号化）で接続する。Azure Database for MySQL は必須
    DB_SSL: bool = False
    # 独自の CA 証明書ファイルを使う場合だけ指定（空なら OS の証明書ストアを使う）
    DB_SSL_CA: str = ""
    CORS_ORIGINS: str = "http://localhost:3000"
    JWT_SECRET: str = "dev-only-secret-change-me-please-32bytes!!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MIN: int = 15
    TAX_ROUNDING: str = "floor"
    # 業務日付の固定（テスト用。空なら当日＝日本時間）
    BUSINESS_DATE: date | None = None

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV.lower() == "prod"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip() and o.strip() != "*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
