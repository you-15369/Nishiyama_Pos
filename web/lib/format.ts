import type { TaxClass } from "./types";

/** 金額表示。計算はしない（サーバの floor 済みの値をそのまま表示する）。 */
export function yen(value: number): string {
  const abs = Math.abs(Math.trunc(value)).toLocaleString("ja-JP");
  return value < 0 ? `−¥${abs}` : `¥${abs}`;
}

/** 税率の表示。税率はマスタで変わるため、サーバが返した適用税率を優先する（FR-012） */
export function taxLabel(taxClass: TaxClass, rate?: number): string {
  if (typeof rate === "number") return `税${Math.round(rate * 1000) / 10}%`;
  return taxClass === "reduced" ? "軽減税率" : "標準税率";
}

/** 商品コード（JAN13桁）の入力チェック */
export function isValidProductCode(code: string): boolean {
  return /^\d{13}$/.test(code);
}
