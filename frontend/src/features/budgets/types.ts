import type { ISODate, ISODateTime, Money } from "../../types";

export interface Budget {
  id: string;
  household: string | null;
  category: string;
  month: ISODate;
  amount: Money;
  spent: Money;
  remaining: Money;
  utilization_pct: Money | null;
  daily_recommended_spend: Money | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface BudgetPayload {
  household?: string | null;
  category: string;
  month: ISODate;
  amount: string;
}
