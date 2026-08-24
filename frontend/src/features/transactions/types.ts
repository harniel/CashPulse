import type { ISODate, ISODateTime, Money } from "../../types";

export type TransactionType = "income" | "expense" | "transfer";

export interface Transaction {
  id: string;
  household: string | null;
  account: string;
  to_account: string | null;
  category: string | null;
  type: TransactionType;
  type_display: string;
  amount: Money;
  currency: string;
  date: ISODate;
  description: string;
  notes: string;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface TransactionPayload {
  household?: string | null;
  account: string;
  to_account?: string | null;
  category?: string | null;
  type: TransactionType;
  amount: string;
  date: ISODate;
  description?: string;
  notes?: string;
}

export interface TransactionFilters {
  account?: string;
  category?: string;
  type?: TransactionType;
  household?: string;
  date_from?: string;
  date_to?: string;
  /** Personal-only (household__isnull) vs. shared — used to scope the
   * list to the active household context (null active household = personal). */
  is_shared?: boolean;
}
