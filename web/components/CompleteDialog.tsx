"use client";

import { useEffect, useRef } from "react";
import { yen } from "@/lib/format";
import type { TransactionResult } from "@/lib/types";

interface Props {
  result: TransactionResult;
  onNext: () => void;
}

/** 購入確定後：税抜・税込合計を表示し、次の会計へ（FR-009, FR-011） */
export default function CompleteDialog({ result, onNext }: Props) {
  const btn = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    btn.current?.focus();
  }, []);
  return (
    <div className="overlay">
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="done-title" onKeyDown={(e) => e.key === "Escape" && onNext()}>
        <span className="hint">取引番号 {result.transaction_id}</span>
        <h2 id="done-title">お会計が完了しました</h2>
        <div className="sum-row">
          <span className="hint">税抜合計</span>
          <span>{yen(result.total_ex_tax)}</span>
        </div>
        {result.total_discount > 0 && (
          <div className="sum-row">
            <span className="hint">会員値引き</span>
            <span>{yen(-result.total_discount)}</span>
          </div>
        )}
        <div className="sum-row">
          <span className="hint">消費税</span>
          <span>{yen(result.tax_by_class.reduced + result.tax_by_class.standard)}</span>
        </div>
        <span className="hint" style={{ marginTop: 8 }}>
          税込合計
        </span>
        <span className="amount">{yen(result.total_in_tax)}</span>
        <button ref={btn} type="button" className="btn btn-dark" onClick={onNext}>
          次の会計へ
        </button>
      </div>
    </div>
  );
}
