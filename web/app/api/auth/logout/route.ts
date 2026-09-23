import { NextResponse, type NextRequest } from "next/server";
import { errorJson, isSameOrigin, TOKEN_COOKIE } from "@/lib/bff";

export async function POST(req: NextRequest) {
  if (!isSameOrigin(req)) return errorJson(403, "FORBIDDEN", "不正なリクエストです");
  const out = new NextResponse(null, { status: 204 });
  out.cookies.set(TOKEN_COOKIE, "", { httpOnly: true, path: "/", maxAge: 0 });
  return out;
}
