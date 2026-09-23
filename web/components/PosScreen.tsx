"use client";

/**
 * レジ画面（/pos）。会員読込 → スキャン → 編集 → 合計確認 → 購入 → 次の会計、を1画面で行う。
 * 金額は常にサーバ（/api/cart/price）の再計算値を表示し、フロントでは計算しない（NFR-012）。
 */
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { api as defaultApi, ApiError, type ApiClient } from "@/lib/apiClient";
import { cartReducer, findItem, initialCart, MAX_QTY, totalQuantity } from "@/lib/cartStore";
import type { Member, Quote, Staff, TransactionResult } from "@/lib/types";
import CartList from "./CartList";
import type { CartItemView } from "./CartItemRow";
import CompleteDialog from "./CompleteDialog";
import ManualCodeInput from "./ManualCodeInput";
import MemberInput from "./MemberInput";
import PurchaseButton from "./PurchaseButton";
import Scanner, { type StartScan } from "./Scanner";
import Toast, { type ToastMessage, type ToastType } from "./Toast";
import TotalPanel from "./TotalPanel";

const isMemberNotFound = (err: unknown) => err instanceof ApiError && err.code === "MEMBER_NOT_FOUND";

interface PricedQuote {
  version: number;
  memberId: string | null;
  quote: Quote;
}

interface Props {
  api?: ApiClient;
  startScan?: StartScan;
}

export default function PosScreen({ api = defaultApi, startScan }: Props) {
  const router = useRouter();
  const routerRef = useRef(router);
  routerRef.current = router;
  const [cart, dispatch] = useReducer(cartReducer, initialCart);
  const [member, setMember] = useState<Member | null>(null);
  const [priced, setPriced] = useState<PricedQuote | null>(null);
  const [staff, setStaff] = useState<Staff | null>(null);
  const [rates, setRates] = useState<{ reduced?: number; standard?: number }>({});
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [purchasing, setPurchasing] = useState(false);
  const [done, setDone] = useState<TransactionResult | null>(null);
  const [session, setSession] = useState(0); // 会計ごとに増やし、登録欄（入力途中の値）を空にする
  const memberRef = useRef<HTMLInputElement>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cartRef = useRef(cart);
  cartRef.current = cart;

  const memberId = member?.member_id ?? null;

  const notify = useCallback((message: string, type: ToastType = "success") => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ id: Date.now(), message, type });
    toastTimer.current = setTimeout(() => setToast(null), type === "error" ? 6000 : 3000);
  }, []);

  /** API エラーの共通処理。401 はログイン画面へ戻す */
  const handleError = useCallback(
    (err: unknown, fallback = "エラーが発生しました") => {
      if (err instanceof ApiError && err.status === 401) {
        routerRef.current.replace("/login");
        return;
      }
      notify(err instanceof ApiError ? err.message : fallback, "error");
    },
    [notify],
  );

  // 担当者と税率の取得
  useEffect(() => {
    api.me().then(setStaff).catch(handleError);
    api
      .taxRates()
      .then((rows) => setRates(Object.fromEntries(rows.map((r) => [r.tax_class, r.rate]))))
      .catch(() => undefined);
  }, [api, handleError]);

  // 購入リストか会員が変わるたびにサーバで再計算（会員を後から読み込んでも全体を再評価：AT-03）
  useEffect(() => {
    if (cart.items.length === 0) {
      setPriced(null);
      return;
    }
    const version = cart.version;
    const items = cart.items.map((i) => ({ product_code: i.code, quantity: i.qty }));
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const quote = await api.price(memberId, items);
        if (!cancelled) setPriced({ version, memberId, quote });
      } catch (err) {
        if (cancelled) return;
        if (isMemberNotFound(err)) {
          setMember(null);
          notify("会員が見つかりません。会員カードを読み直してください", "error");
          return;
        }
        handleError(err, "金額を計算できませんでした");
      }
    }, 120);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [api, cart.version, cart.items, memberId, handleError, notify]);

  const fresh = priced !== null && priced.version === cart.version && priced.memberId === memberId;
  const pending = cart.items.length > 0 && !fresh;

  // 表示用の明細（計算中は直前の値引き単価を仮に使う）
  const views: CartItemView[] = useMemo(() => {
    const lines = new Map((priced?.quote.lines ?? []).map((l) => [l.product_code, l]));
    return cart.items.map((i) => {
      const line = lines.get(i.code);
      const unitDiscount = line && line.quantity > 0 ? Math.floor(line.discount_amount / line.quantity) : 0;
      const discount = fresh && line ? line.discount_amount : unitDiscount * i.qty;
      return {
        code: i.code,
        name: i.name,
        unitPrice: i.unitPrice,
        qty: i.qty,
        taxClass: i.taxClass,
        appliedRate: line?.applied_rate ?? rates[i.taxClass],
        discount,
        subtotal: fresh && line ? line.subtotal : i.unitPrice * i.qty - discount,
      };
    });
  }, [cart.items, priced, fresh, rates]);

  /** スキャン・手入力の共通経路（FR-003, FR-004, FR-005） */
  const addByCode = useCallback(
    async (code: string): Promise<boolean> => {
      const existing = findItem(cartRef.current, code);
      if (existing) {
        if (existing.qty >= MAX_QTY) {
          notify(`${existing.name} は ${MAX_QTY} 点までです`, "error");
          return false;
        }
        dispatch({ type: "add", product: { product_code: code, name: existing.name, unit_price: existing.unitPrice, tax_class: existing.taxClass } });
        notify(`1件追加しました（合計${totalQuantity(cartRef.current) + 1}点）`);
        return true;
      }
      try {
        const product = await api.getProduct(code);
        dispatch({ type: "add", product });
        notify(`1件追加しました（合計${totalQuantity(cartRef.current) + 1}点）`);
        return true;
      } catch (err) {
        if (err instanceof ApiError && (err.status === 404 || err.status === 400)) {
          notify(`商品がマスタ未登録です（${code}）`, "error");
          return false;
        }
        handleError(err);
        return false;
      }
    },
    [api, notify, handleError],
  );

  const loadMember = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        const m = await api.getMember(id);
        setMember(m);
        notify(`会員を読み込みました（${m.name} 様）`);
        return true;
      } catch (err) {
        if (err instanceof ApiError && (err.status === 404 || err.status === 400)) {
          // 存在しない会員IDは受け付けない（読み込み済みの会員はそのまま）
          notify(`会員が見つかりません（${id}）。会員IDを確認してください`, "error");
          return false;
        }
        handleError(err);
        return false;
      }
    },
    [api, notify, handleError],
  );

  const purchase = useCallback(async () => {
    if (!priced || !fresh || cart.items.length === 0) return;
    setPurchasing(true);
    const items = cart.items.map((i) => ({ product_code: i.code, quantity: i.qty }));
    try {
      const result = await api.purchase(memberId, items, priced.quote.total_in_tax);
      dispatch({ type: "clear" }); // FR-011 登録欄をクリア
      setMember(null);
      setPriced(null);
      setToast(null);
      setSession((n) => n + 1);
      setDone(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422 && err.data) {
        // 金額不一致：サーバ再計算値でカートを同期し、その金額でもう一度購入してもらう
        const quote = err.data as Quote;
        dispatch({ type: "syncFromServer", lines: quote.lines });
        setPriced({ version: cart.version + 1, memberId: quote.member_id, quote });
        if (quote.member_id === null && memberId !== null) setMember(null);
        notify("金額を更新しました。表示の金額でもう一度「購入する」を押してください", "info");
      } else if (isMemberNotFound(err)) {
        setMember(null);
        notify("会員が見つかりません。会員カードを読み直してから購入してください", "error");
      } else if (err instanceof ApiError && err.status === 404) {
        notify("マスタにない商品が含まれています。リストを確認してください", "error");
      } else {
        handleError(err, "購入を確定できませんでした");
      }
    } finally {
      setPurchasing(false);
    }
  }, [api, cart.items, cart.version, fresh, memberId, notify, priced, handleError]);

  const nextCustomer = useCallback(() => {
    setDone(null);
    setTimeout(() => memberRef.current?.focus(), 0);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      router.replace("/login");
    }
  }, [api, router]);

  const shownQuote = priced?.quote ?? null;

  return (
    <div className="pos">
      <header className="pos-header">
        <div className="brand">POS</div>
        <div className="sub">簡易レジ</div>
        <Toast toast={toast} />
        <div className="staff">
          {staff ? (
            <>
              {staff.name}
              <span className="staff-id"> / {staff.login_id}</span>
            </>
          ) : (
            ""
          )}
        </div>
        <button type="button" className="btn-link" onClick={logout}>
          ログアウト
        </button>
      </header>

      <main className="pos-main">
        <aside className="pos-side" aria-label="会員と商品の登録">
          <MemberInput
            key={`member-${session}`}
            memberId={memberId}
            memberName={member?.name ?? null}
            onLoad={loadMember}
            onClear={() => setMember(null)}
            inputRef={memberRef}
          />
          <div className="pos-block" style={{ gap: 12 }}>
            <Scanner onScan={addByCode} startScan={startScan} />
            <ManualCodeInput key={`code-${session}`} onAdd={addByCode} />
          </div>
        </aside>

        <CartList
          items={views}
          totalQty={totalQuantity(cart)}
          selectedCode={cart.selectedCode}
          onSelect={(code) => dispatch({ type: "select", code })}
          onQty={(code, qty) => dispatch({ type: "changeQty", code, qty })}
          onRemove={(code) => dispatch({ type: "remove", code })}
        />

        <TotalPanel quote={cart.items.length ? shownQuote : null} rates={rates} pending={pending}>
          <PurchaseButton onPurchase={purchase} disabled={cart.items.length === 0 || !fresh} busy={purchasing} />
        </TotalPanel>
      </main>

      {done && <CompleteDialog result={done} onNext={nextCustomer} />}
    </div>
  );
}
