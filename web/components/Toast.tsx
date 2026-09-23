"use client";

export type ToastType = "success" | "info" | "error";
export interface ToastMessage {
  id: number;
  message: string;
  type: ToastType;
}

/** スキャン結果などの即時フィードバック */
export default function Toast({ toast }: { toast: ToastMessage | null }) {
  return (
    <div className="toast-slot" role="status" aria-live="polite">
      {toast && (
        <div key={toast.id} className="toast" data-type={toast.type}>
          {toast.message}
        </div>
      )}
    </div>
  );
}
