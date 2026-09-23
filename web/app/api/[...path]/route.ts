/**
 * BFF: 業務APIのプロキシ。Cookie のトークンを Authorization ヘッダに載せ替えて FastAPI に転送する。
 * 転送してよいパスだけを許可し、それ以外は 404（任意のパスへの中継をさせない）。
 */
import { type NextRequest } from "next/server";
import { apiBaseUrl, errorJson, forward, isSameOrigin, TOKEN_COOKIE } from "@/lib/bff";

type Ctx = { params: Promise<{ path: string[] }> };

const SEGMENT = /^[A-Za-z0-9\-]{1,20}$/;

const ALLOWED: { method: "GET" | "POST"; match: (p: string[]) => boolean }[] = [
  { method: "GET", match: (p) => p.length === 2 && p[0] === "auth" && p[1] === "me" },
  { method: "GET", match: (p) => p.length === 2 && p[0] === "members" && SEGMENT.test(p[1]) },
  { method: "GET", match: (p) => p.length === 2 && p[0] === "products" && SEGMENT.test(p[1]) },
  { method: "GET", match: (p) => p.length === 1 && p[0] === "tax-rates" },
  { method: "POST", match: (p) => p.length === 2 && p[0] === "cart" && p[1] === "price" },
  { method: "POST", match: (p) => p.length === 1 && p[0] === "transactions" },
];

async function handle(req: NextRequest, ctx: Ctx, method: "GET" | "POST") {
  const { path } = await ctx.params;
  if (!ALLOWED.some((a) => a.method === method && a.match(path))) {
    return errorJson(404, "NOT_FOUND", "Not Found");
  }
  if (method === "POST" && !isSameOrigin(req)) return errorJson(403, "FORBIDDEN", "不正なリクエストです");

  const token = req.cookies.get(TOKEN_COOKIE)?.value;
  if (!token) return errorJson(401, "UNAUTHORIZED", "ログインが必要です");

  const url = `${apiBaseUrl()}/api/${path.map(encodeURIComponent).join("/")}`;
  return forward(url, {
    method,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: method === "POST" ? await req.text() : undefined,
  });
}

export function GET(req: NextRequest, ctx: Ctx) {
  return handle(req, ctx, "GET");
}

export function POST(req: NextRequest, ctx: Ctx) {
  return handle(req, ctx, "POST");
}
