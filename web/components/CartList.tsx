"use client";

import CartItemRow, { type CartItemView } from "./CartItemRow";

interface Props {
  items: CartItemView[];
  totalQty: number;
  selectedCode: string | null;
  onSelect: (code: string) => void;
  onQty: (code: string, qty: number) => void;
  onRemove: (code: string) => void;
}

export default function CartList({ items, totalQty, selectedCode, onSelect, onQty, onRemove }: Props) {
  return (
    <section className="pos-list" aria-labelledby="cart-title">
      <div className="pos-list-head">
        <h1 id="cart-title">購入リスト</h1>
        <span className="count">
          {items.length}品目 · {totalQty}点
        </span>
        {items.length > 0 && <span className="hint list-hint">商品を押すと数量変更・削除</span>}
      </div>
      {items.length === 0 ? (
        <div className="empty">
          商品をスキャンするか、
          <br />
          商品コードを入力してください
        </div>
      ) : (
        <ul className="tiles" style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {items.map((item) => (
            <CartItemRow
              key={item.code}
              item={item}
              selected={item.code === selectedCode}
              onSelect={onSelect}
              onQty={onQty}
              onRemove={onRemove}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
