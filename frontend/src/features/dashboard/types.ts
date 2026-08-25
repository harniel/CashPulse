import type { ISODate, Money } from "../../types";

export interface CashFlowMonth {
  month: ISODate;
  income: Money;
  expense: Money;
  net: Money;
}

export interface NetWorthMonth {
  month: ISODate;
  net_worth: Money;
}

export interface SpendingByCategory {
  category_id: string;
  category: string;
  amount: Money;
}

export interface BudgetUtilization {
  budget_id: string;
  category: string;
  amount: Money;
  spent: Money;
  utilization_pct: Money | null;
}

export type InsightType =
  | "budget_exceeded"
  | "budget_approaching"
  | "negative_cash_flow";

export interface Insight {
  type: InsightType;
  category?: string;
  message: string;
}

export interface DashboardSummary {
  scope: { household: string | null };
  month: ISODate;
  net_cash_flow: Money;
  savings_rate_pct: Money | null;
  net_worth: Money;
  charts: {
    cash_flow_by_month: CashFlowMonth[];
    spending_by_category: SpendingByCategory[];
    net_worth_by_month: NetWorthMonth[];
    budget_utilization: BudgetUtilization[];
  };
  insights: Insight[];
}
