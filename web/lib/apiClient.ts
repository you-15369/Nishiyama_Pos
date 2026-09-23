/**
 * ApiClient：サーバ通信をここに集約する。ブラウザは BFF（同一オリジンの /api/*）だけを呼ぶ。
 * トークンは HttpOnly Cookie にあり、JavaScript からは読めない（NFR-008, NFR-015）。
 */
import type { Member, Product, Quote, Staff, TransactionResult } from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public data?: unknown,
  ) {
    super(message);
  }
}

type Fetcher = typeof fetch;

export interface CartLineInput {
  product_code: string;
  quantity: number;
}

async function request<T>(fetcher: Fetcher, path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetcher(path, {
      ...init,
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "サーバーに接続できません。通信状況を確認してください");
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = body?.error ?? {};
    throw new ApiError(res.status, err.code ?? "HTTP_ERROR", err.message ?? "エラーが発生しました", body?.data);
  }
  return body as T;
}

export function createApiClient(fetcher: Fetcher = (...args) => fetch(...args)) {
  return {
    login: (login_id: string, password: string) =>
      request<{ staff: Staff }>(fetcher, "/api/auth/login", { method: "POST", body: JSON.stringify({ login_id, password }) }),
    logout: () => request<void>(fetcher, "/api/auth/logout", { method: "POST" }),
    me: () => request<Staff>(fetcher, "/api/auth/me"),
    taxRates: async () =>
      (await request<{ data: { tax_class: "standard" | "reduced"; rate: number }[] }>(fetcher, "/api/tax-rates")).data,
    getMember: (id: string) => request<Member>(fetcher, `/api/members/${encodeURIComponent(id)}`),
    getProduct: (code: string) => request<Product>(fetcher, `/api/products/${encodeURIComponent(code)}`),
    price: async (member_id: string | null, items: CartLineInput[]) =>
      (await request<{ data: Quote }>(fetcher, "/api/cart/price", { method: "POST", body: JSON.stringify({ member_id, items }) })).data,
    purchase: async (member_id: string | null, items: CartLineInput[], client_total_in_tax: number) =>
      (
        await request<{ data: TransactionResult }>(fetcher, "/api/transactions", {
          method: "POST",
          body: JSON.stringify({ member_id, items, client_total_in_tax }),
        })
      ).data,
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
export const api = createApiClient();
