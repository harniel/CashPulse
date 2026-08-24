import { client } from "../../api/client";
import type { PaginatedResponse } from "../../types";
import type { Transaction, TransactionFilters, TransactionPayload } from "./types";

export function fetchTransactions(
  params: TransactionFilters & { page?: number } = {},
): Promise<PaginatedResponse<Transaction>> {
  return client.get<PaginatedResponse<Transaction>>("/transactions/", { params }).then((r) => r.data);
}

export function createTransaction(payload: TransactionPayload): Promise<Transaction> {
  return client.post<Transaction>("/transactions/", payload).then((r) => r.data);
}

export function updateTransaction(
  id: string,
  payload: Partial<TransactionPayload>,
): Promise<Transaction> {
  return client.patch<Transaction>(`/transactions/${id}/`, payload).then((r) => r.data);
}

export function deleteTransaction(id: string): Promise<void> {
  return client.delete(`/transactions/${id}/`).then(() => undefined);
}
