"""共通エラー形式 {"error": {"code", "message", "details"}} に揃える（仕様設計書 §3.5）。"""
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: list[Any] | None = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []
        self.data = data
        self.headers = headers


def _body(code: str, message: str, details: list[Any] | None = None, data: Any = None) -> dict:
    body: dict[str, Any] = {"error": {"code": code, "message": message, "details": details or []}}
    if data is not None:
        body["data"] = data
    return body


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status,
            content=_body(exc.code, exc.message, exc.details, exc.data),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        # 入力値そのものはエコーしない（ログ・画面への注入を避ける）
        details = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", "")} for e in exc.errors()]
        return JSONResponse(status_code=400, content=_body("VALIDATION_ERROR", "入力値が正しくありません", details))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {401: "UNAUTHORIZED", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)), headers=exc.headers)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # 画面には詳細を出さず、API のターミナルに原因を出す
        logging.getLogger("uvicorn.error").exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content=_body("INTERNAL_ERROR", "サーバーエラーが発生しました"))
