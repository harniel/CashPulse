import type { ISODateTime } from "../../types";

export type BudgetImportBatchStatus = "pending" | "confirmed";
export type BudgetImportRowStatus = "pending" | "imported" | "failed" | "skipped";
export type BudgetImportRowAction = "create" | "update" | "";

export interface BudgetImportBatch {
  id: string;
  filename: string;
  status: BudgetImportBatchStatus;
  row_count: number;
  created_at: ISODateTime;
}

export interface BudgetImportRowData {
  category: string;
  month: string;
  amount: string;
  household: string;
}

export interface BudgetImportRow {
  id: string;
  row_number: number;
  raw_data: BudgetImportRowData;
  status: BudgetImportRowStatus;
  action: BudgetImportRowAction;
  error: string;
  budget: string | null;
  created_at: ISODateTime;
}

export interface ConfirmBudgetImportResult {
  imported_count: number;
  batch: BudgetImportBatch;
}
