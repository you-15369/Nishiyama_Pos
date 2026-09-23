/** BFF: ログイン。FastAPI で認証し、JWT を HttpOnly Cookie に保存する（トークンはブラウザJSに渡さない）。 */
import { NextResponse, type NextRequest } from "next/server";
import { apiBaseUrl, cookieSecure, errorJson, isSameOrigin, TOKEN_COOKIE } from "@/lib/bff";

export async function POST(req: NextRequest) {
  if (!isSameOrigin(req)) return errorJson(403, "FORBIDDEN", "不正なリクエストです");
  const body = await req.text();
  let res: Response;
  try {
    res = await fetch(`${apiBaseUrl()}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return errorJson(502, "UPSTREAM_UNAVAILABLE", "サーバーに接続できません。しばらくしてから再度お試しください");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return NextResponse.json(data, { status: res.status });

  const out = NextResponse.json({ staff: data.staff });
  out.cookies.set(TOKEN_COOKIE, data.access_token, {
    httpOnly: true,
    secure: cookieSecure(),
    sameSite: "lax",
    path: "/",
    maxAge: data.expires_in,
  });
  return out;
}
