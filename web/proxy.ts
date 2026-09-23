/** 未ログインでレジ画面を開いたらログイン画面へ。トークンの検証自体は FastAPI が行う。 */
import { NextResponse, type NextRequest } from "next/server";

export function proxy(req: NextRequest) {
  const hasToken = Boolean(req.cookies.get("pos_token")?.value);
  if (!hasToken) {
    const url = new URL("/login", req.url);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/pos/:path*"],
};
