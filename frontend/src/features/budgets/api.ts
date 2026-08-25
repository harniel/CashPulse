import { client } from "../../api/client";
import type { PaginatedResponse } from "../../types";
import type { Budget, BudgetPayload } from "./types";

export interface BudgetListParams {
  month?: string; // "YYYY-MM"
  household?: string;
  // No `is_shared` filter on this endpoint (unlike /transactions/) — the
  // "personal only" case is handled by filtering client-side to
  // household === null after fetching (see features/budgets/hooks.ts).
}

export function fetchBudgets(params: BudgetListParams = {}): Promise<Budget[]> {
  return client.get<PaginatedResponse<Budget>>("/budgets/", { params }).then((r) => r.data.results);
}

export function fetchBudgetPerformance(id: string): Promise<Budget[]> {
  return client.get<Budget[]>(`/budgets/${id}/performance/`).then((r) => r.data);
}

export function createBudget(payload: BudgetPayload): Promise<Budget> {
  return client.post<Budget>("/budgets/", payload).then((r) => r.data);
}

export function updateBudget(id: string, payload: Partial<BudgetPayload>): Promise<Budget> {
  return client.patch<Budget>(`/budgets/${id}/`, payload).then((r) => r.data);
}

export function deleteBudget(id: string): Promise<void> {
  return client.delete(`/budgets/${id}/`).then(() => undefined);
}
