/** BFF（サーバ側のみ）で使う共通処理。このファイルはブラウザに配信されない。 */
import "server-only";
import { NextResponse, type NextRequest } from "next/server";

export const TOKEN_COOKIE = "pos_token";

export function apiBaseUrl(): string {
  return (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
}

export function cookieSecure(): boolean {
  const v = process.env.COOKIE_SECURE;
  if (v === "true") return true;
  if (v === "false") return false;
  return process.env.NODE_ENV === "production";
}

export function errorJson(status: number, code: string, message: string) {
  return NextResponse.json({ error: { code, message, details: [] } }, { status });
}

/**
 * 状態を変える POST は同一オリジンからだけ受け付ける（CSRF 対策。SameSite=Lax と併用）。
 */
export function isSameOrigin(req: NextRequest): boolean {
  const origin = req.headers.get("origin");
  if (!origin) return true; // 同一オリジンの fetch で Origin が付かないブラウザもある
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

/** FastAPI への転送。レスポンスの本文とステータスをそのまま返す。 */
export async function forward(url: string, init: RequestInit): Promise<Response> {
  try {
    const res = await fetch(url, { ...init, cache: "no-store", signal: AbortSignal.timeout(10_000) });
    const body = await res.text();
    return new Response(body || null, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return errorJson(502, "UPSTREAM_UNAVAILABLE", "サーバーに接続できません。しばらくしてから再度お試しください");
  }
}
