"use client";

import { MAX_QTY, MIN_QTY } from "@/lib/cartStore";
import { taxLabel, yen } from "@/lib/format";
import type { TaxClass } from "@/lib/types";

export interface CartItemView {
  code: string;
  name: string;
  unitPrice: number;
  qty: number;
  taxClass: TaxClass;
  appliedRate?: number;
  discount: number;
  subtotal: number; // 値引き後・税抜（サーバ値。未計算時は単価×数量）
}

interface Props {
  item: CartItemView;
  selected: boolean;
  onSelect: (code: string) => void;
  onQty: (code: string, qty: number) => void;
  onRemove: (code: string) => void;
}

/** 購入リストの1商品（タイル表示） */
export default function CartItemRow({ item, selected, onSelect, onQty, onRemove }: Props) {
  const gross = item.unitPrice * item.qty;
  const discounted = item.discount > 0;
  return (
    <li className="tile" data-selected={selected}>
      {selected ? (
        <div className="tile-visual selected">
          <div className="stepper" role="group" aria-label={`${item.name}の数量`}>
            <button type="button" aria-label="数量を減らす" disabled={item.qty <= MIN_QTY} onClick={() => onQty(item.code, item.qty - 1)}>
              −
            </button>
            <output aria-live="polite">{item.qty}</output>
            <button type="button" aria-label="数量を増やす" disabled={item.qty >= MAX_QTY} onClick={() => onQty(item.code, item.qty + 1)}>
              ＋
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="tile-visual" onClick={() => onSelect(item.code)} aria-label={`${item.name}を選択`}>
          <span>{item.code}</span>
          {discounted && <span className="tag">会員 {yen(-item.discount)}</span>}
        </button>
      )}
      <button type="button" className="tile-info" onClick={() => onSelect(item.code)} aria-pressed={selected}>
        <span className="tile-name">
          <span>{item.name}</span>
          <span>
            {yen(item.subtotal)}
            {discounted && <span className="strike">{yen(gross)}</span>}
          </span>
        </span>
      </button>
      <div className="tile-meta">
        <span>
          {yen(item.unitPrice)} × {item.qty} · {taxLabel(item.taxClass, item.appliedRate)}
        </span>
        {selected && (
          <button type="button" className="btn-link" style={{ height: 28, fontSize: 12 }} onClick={() => onRemove(item.code)}>
            削除
          </button>
        )}
      </div>
    </li>
  );
}
