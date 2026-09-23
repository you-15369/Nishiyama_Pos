"use client";

import { yen } from "@/lib/format";
import type { Quote } from "@/lib/types";

interface Props {
  quote: Quote | null;
  rates: { reduced?: number; standard?: number };
  pending: boolean;
  children?: React.ReactNode;
}

function pct(rate?: number) {
  return typeof rate === "number" ? `${Math.round(rate * 1000) / 10}%` : "";
}

/** 合計表示（税抜・値引き・区分別税額・税込）。値はすべてサーバ再計算値（FR-008, NFR-012） */
export default function TotalPanel({ quote, rates, pending, children }: Props) {
  const q = quote;
  return (
    <aside className="pos-summary" aria-label="お会計">
      <div className="title">お会計</div>
      <dl style={{ margin: 0, display: "contents" }}>
        <div className="sum-row">
          <dt>税抜合計</dt>
          <dd>{yen(q?.total_ex_tax ?? 0)}</dd>
        </div>
        <div className="sum-row">
          <dt>会員値引き</dt>
          <dd>{q && q.total_discount > 0 ? yen(-q.total_discount) : "—"}</dd>
        </div>
        <div className="sum-row">
          <dt>
            消費税 {pct(rates.reduced)}（{yen(q?.taxable_by_class.reduced ?? 0)}）
          </dt>
          <dd>{yen(q?.tax_by_class.reduced ?? 0)}</dd>
        </div>
        <div className="sum-row">
          <dt>
            消費税 {pct(rates.standard)}（{yen(q?.taxable_by_class.standard ?? 0)}）
          </dt>
          <dd>{yen(q?.tax_by_class.standard ?? 0)}</dd>
        </div>
      </dl>
      <div className="sum-total">
        <span className="caption">
          <span>税込合計</span>
          {pending && <span aria-live="polite">計算中…</span>}
        </span>
        <span className="amount" data-testid="total-in-tax">
          {yen(q?.total_in_tax ?? 0)}
        </span>
      </div>
      {children}
    </aside>
  );
}
