import type { ISODateTime, Money } from "../../types";

export type AccountType =
  | "cash"
  | "bank"
  | "e_wallet"
  | "credit_card"
  | "savings"
  | "loan"
  | "investment";

export const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  cash: "Cash",
  bank: "Bank account",
  e_wallet: "E-wallet",
  credit_card: "Credit card",
  savings: "Savings account",
  loan: "Loan account",
  investment: "Investment account",
};

export interface Account {
  id: string;
  name: string;
  account_type: AccountType;
  account_type_display: string;
  currency: string;
  institution: string;
  is_active: boolean;
  balance: Money;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface AccountPayload {
  name: string;
  account_type: AccountType;
  currency: string;
  institution?: string;
  is_active?: boolean;
}
