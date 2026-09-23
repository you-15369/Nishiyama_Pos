/** UT-FE-01〜03 CartStore */
import { cartReducer, initialCart, totalQuantity, type CartState } from "@/lib/cartStore";
import type { Product } from "@/lib/types";

const onigiri: Product = { product_code: "4901234567894", name: "おにぎり", unit_price: 150, tax_class: "reduced" };
const pen: Product = { product_code: "4909999999999", name: "ボールペン", unit_price: 200, tax_class: "standard" };

const add = (s: CartState, p: Product) => cartReducer(s, { type: "add", product: p });

describe("CartStore", () => {
  it("同一商品は数量が加算される", () => {
    const s = add(add(initialCart, onigiri), onigiri);
    expect(s.items).toHaveLength(1);
    expect(s.items[0].qty).toBe(2);
    expect(totalQuantity(s)).toBe(2);
  });

  it("数量は1〜99、0は削除", () => {
    const s = add(initialCart, onigiri);
    const code = onigiri.product_code;
    expect(cartReducer(s, { type: "changeQty", code, qty: 1 }).items[0].qty).toBe(1);
    const s99 = cartReducer(s, { type: "changeQty", code, qty: 99 });
    expect(s99.items[0].qty).toBe(99);
    expect(cartReducer(s99, { type: "changeQty", code, qty: 100 }).items[0].qty).toBe(99); // 100は不可
    expect(add(s99, onigiri).items[0].qty).toBe(99); // スキャンでも99で止まる
    expect(cartReducer(s, { type: "changeQty", code, qty: 0 }).items).toHaveLength(0); // 0は削除
  });

  it("選択と削除", () => {
    let s = add(add(initialCart, onigiri), pen);
    s = cartReducer(s, { type: "select", code: onigiri.product_code });
    expect(s.selectedCode).toBe(onigiri.product_code);
    s = cartReducer(s, { type: "select", code: pen.product_code });
    expect(s.selectedCode).toBe(pen.product_code); // 選択は常に1件
    const before = s.version;
    s = cartReducer(s, { type: "remove", code: pen.product_code });
    expect(s.items.map((i) => i.code)).toEqual([onigiri.product_code]);
    expect(s.selectedCode).toBeNull();
    expect(s.version).toBeGreaterThan(before); // 変更で再計算が走る
  });

  it("サーバ値で同期できる", () => {
    const s = add(initialCart, onigiri);
    const synced = cartReducer(s, {
      type: "syncFromServer",
      lines: [{ product_code: onigiri.product_code, name: "おにぎり 鮭", unit_price: 160, quantity: 1, discount_amount: 0, tax_class: "reduced", applied_rate: 0.08, subtotal: 160 }],
    });
    expect(synced.items[0]).toMatchObject({ name: "おにぎり 鮭", unitPrice: 160 });
  });
});
