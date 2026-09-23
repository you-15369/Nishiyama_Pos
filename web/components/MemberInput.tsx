"use client";

import { useState } from "react";

interface Props {
  memberName: string | null;
  memberId: string | null;
  /** 読み込めたら true。見つからなければ false（入力欄は消さずに直してもらう） */
  onLoad: (id: string) => Promise<boolean> | boolean;
  onClear: () => void;
  inputRef?: React.Ref<HTMLInputElement>;
}

/** 会員カード（会員ID）の読み込み（FR-002）。存在しない会員IDでは会計できない。会員カードなしなら会員なしで会計できる */
export default function MemberInput({ memberName, memberId, onLoad, onClear, inputRef }: Props) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const id = value.trim();
  const valid = /^[A-Za-z0-9-]{1,20}$/.test(id);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid || busy) return;
    setBusy(true);
    try {
      if (await onLoad(id)) setValue("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="pos-block" onSubmit={submit}>
      <label htmlFor="member-id" className="label">
        会員カード
      </label>
      <div className="input-row">
        <input
          id="member-id"
          ref={inputRef}
          className="field"
          autoComplete="off"
          maxLength={20}
          placeholder={memberId ?? "M0001"}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <button type="submit" className="btn" disabled={!valid || busy}>
          読込
        </button>
      </div>
      <div className="member-status" aria-live="polite">
        {memberName ? (
          <>
            <span>{memberName} 様</span>
            <span className="muted">— 会員価格</span>
            <button type="button" className="btn-link" style={{ height: 28, marginLeft: "auto", fontSize: 12 }} onClick={onClear}>
              解除
            </button>
          </>
        ) : (
          <span className="muted">会員なし</span>
        )}
      </div>
    </form>
  );
}
