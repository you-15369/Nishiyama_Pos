export type TaxClass = "standard" | "reduced";

export interface Product {
  product_code: string;
  name: string;
  unit_price: number;
  tax_class: TaxClass;
}

export interface Member {
  member_id: string;
  name: string;
}

export interface Staff {
  staff_id: number;
  login_id: string;
  name: string;
}

export interface QuoteLine {
  product_code: string;
  name: string;
  unit_price: number;
  quantity: number;
  discount_amount: number;
  tax_class: TaxClass;
  applied_rate: number;
  subtotal: number;
}

export interface TaxByClass {
  reduced: number;
  standard: number;
}

export interface Quote {
  member_id: string | null;
  lines: QuoteLine[];
  total_ex_tax: number;
  total_discount: number;
  taxable_by_class: TaxByClass;
  tax_by_class: TaxByClass;
  total_in_tax: number;
}

export interface TransactionResult {
  transaction_id: number;
  total_ex_tax: number;
  total_discount: number;
  total_in_tax: number;
  tax_by_class: TaxByClass;
  transacted_at: string;
}
