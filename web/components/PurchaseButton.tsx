"use client";

interface Props {
  onPurchase: () => void;
  disabled: boolean;
  busy: boolean;
}

export default function PurchaseButton({ onPurchase, disabled, busy }: Props) {
  return (
    <button type="button" className="btn btn-dark purchase" onClick={onPurchase} disabled={disabled || busy}>
      {busy ? "確定しています…" : "購入する"}
    </button>
  );
}
