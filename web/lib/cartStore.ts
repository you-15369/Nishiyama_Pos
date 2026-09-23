/**
 * CartStore：購入リストの状態を一元管理する純粋なリデューサ（仕様設計書 §2.5）。
 * 金額の計算はしない。金額・値引き・税はサーバの再計算値（Quote）を表示する。
 */
import type { Product, QuoteLine, TaxClass } from "./types";

export const MIN_QTY = 1;
export const MAX_QTY = 99;

export interface CartItem {
  code: string;
  name: string;
  unitPrice: number;
  taxClass: TaxClass;
  qty: number;
}

export interface CartState {
  items: CartItem[];
  selectedCode: string | null;
  /** 変更のたびに増える。価格計算の結果がどの状態に対するものかを判定するのに使う */
  version: number;
}

export type CartAction =
  | { type: "add"; product: Product }
  | { type: "changeQty"; code: string; qty: number }
  | { type: "remove"; code: string }
  | { type: "select"; code: string | null }
  | { type: "syncFromServer"; lines: QuoteLine[] }
  | { type: "clear" };

export const initialCart: CartState = { items: [], selectedCode: null, version: 0 };

function bump(state: CartState, patch: Partial<CartState>): CartState {
  return { ...state, ...patch, version: state.version + 1 };
}

export function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case "add": {
      const p = action.product;
      const existing = state.items.find((i) => i.code === p.product_code);
      if (existing) {
        // 同一商品は行を増やさず数量+1（上限99）
        if (existing.qty >= MAX_QTY) return state;
        return bump(state, {
          items: state.items.map((i) => (i.code === p.product_code ? { ...i, qty: i.qty + 1 } : i)),
          selectedCode: p.product_code,
        });
      }
      const item: CartItem = { code: p.product_code, name: p.name, unitPrice: p.unit_price, taxClass: p.tax_class, qty: 1 };
      return bump(state, { items: [...state.items, item], selectedCode: p.product_code });
    }
    case "changeQty": {
      if (!Number.isFinite(action.qty)) return state;
      const qty = Math.trunc(action.qty);
      if (qty < MIN_QTY) return cartReducer(state, { type: "remove", code: action.code }); // 0 は削除として扱う
      if (qty > MAX_QTY) return state; // 100 以上は不可（99 のまま）
      const target = state.items.find((i) => i.code === action.code);
      if (!target || target.qty === qty) return state;
      return bump(state, { items: state.items.map((i) => (i.code === action.code ? { ...i, qty } : i)) });
    }
    case "remove": {
      if (!state.items.some((i) => i.code === action.code)) return state;
      return bump(state, {
        items: state.items.filter((i) => i.code !== action.code),
        selectedCode: state.selectedCode === action.code ? null : state.selectedCode,
      });
    }
    case "select": {
      // 選択は常に1件（排他）。同じ行をもう一度押すと選択解除
      const next = action.code === state.selectedCode ? null : action.code;
      return { ...state, selectedCode: next };
    }
    case "syncFromServer": {
      // 422（金額不一致）時：サーバ再計算値でカートを同期する
      const items: CartItem[] = action.lines.map((l) => ({
        code: l.product_code,
        name: l.name,
        unitPrice: l.unit_price,
        taxClass: l.tax_class,
        qty: l.quantity,
      }));
      const selectedCode = items.some((i) => i.code === state.selectedCode) ? state.selectedCode : null;
      return bump(state, { items, selectedCode });
    }
    case "clear":
      return bump(state, { items: [], selectedCode: null });
    default:
      return state;
  }
}

export function totalQuantity(state: CartState): number {
  return state.items.reduce((sum, i) => sum + i.qty, 0);
}

export function findItem(state: CartState, code: string): CartItem | undefined {
  return state.items.find((i) => i.code === code);
}
