"""FastAPI エントリポイント。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .errors import install_error_handlers
from .routers import auth, cart, members, products, tax_rates, transactions


def create_app() -> FastAPI:
    s = get_settings()
    # 本番では Swagger / ReDoc / OpenAPI を無効化（NFR-013）
    docs = {} if not s.is_prod else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(title="簡易POS API", version="2.0.0", **docs)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list,  # * は使わない（NFR-015）
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )
    install_error_handlers(app)

    for r in (auth.router, members.router, products.router, cart.router, transactions.router, tax_rates.router):
        app.include_router(r)

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()
