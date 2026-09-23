"use client";

import { useState } from "react";
import { isValidProductCode } from "@/lib/format";

interface Props {
  onAdd: (code: string) => Promise<boolean> | boolean;
  inputRef?: React.Ref<HTMLInputElement>;
}

/** 商品コードの手入力（FR-004）。USB/Bluetooth のバーコードリーダー（キーボード入力＋Enter）にも使える */
export default function ManualCodeInput({ onAdd, inputRef }: Props) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const trimmed = code.trim();
  const valid = isValidProductCode(trimmed);
  const showError = trimmed.length > 0 && !/^\d*$/.test(trimmed);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid || busy) return;
    setBusy(true);
    try {
      const ok = await onAdd(trimmed);
      if (ok) setCode("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="pos-block" onSubmit={submit} style={{ gap: 6 }}>
      <label htmlFor="manual-code" className="hint">
        読めない場合は商品コード（13桁）を入力
      </label>
      <div className="input-row">
        <input
          id="manual-code"
          ref={inputRef}
          className="field"
          inputMode="numeric"
          autoComplete="off"
          placeholder="4900000000000"
          maxLength={13}
          value={code}
          aria-invalid={showError}
          aria-describedby={showError ? "manual-code-error" : undefined}
          onChange={(e) => setCode(e.target.value.replace(/\s/g, ""))}
        />
        <button type="submit" className="btn btn-dark" disabled={!valid || busy}>
          追加
        </button>
      </div>
      {showError && (
        <span id="manual-code-error" className="error-text">
          数字13桁で入力してください
        </span>
      )}
    </form>
  );
}
