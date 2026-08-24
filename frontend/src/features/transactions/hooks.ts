import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "./api";
import type { TransactionFilters, TransactionPayload } from "./types";

const TRANSACTIONS_KEY = ["transactions"];

export function useTransactions(filters: TransactionFilters, page: number) {
  return useQuery({
    queryKey: [...TRANSACTIONS_KEY, filters, page],
    queryFn: () => api.fetchTransactions({ ...filters, page }),
    placeholderData: (previous) => previous,
  });
}

function invalidateTransactionRelated(queryClient: ReturnType<typeof useQueryClient>) {
  // A transaction write can change account balances, budget spend, and
  // the dashboard summary — invalidate the whole neighborhood, not just
  // the transactions list itself.
  queryClient.invalidateQueries({ queryKey: TRANSACTIONS_KEY });
  queryClient.invalidateQueries({ queryKey: ["accounts"] });
  queryClient.invalidateQueries({ queryKey: ["budgets"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createTransaction,
    onSuccess: () => invalidateTransactionRelated(queryClient),
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<TransactionPayload> }) =>
      api.updateTransaction(id, payload),
    onSuccess: () => invalidateTransactionRelated(queryClient),
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteTransaction,
    onSuccess: () => invalidateTransactionRelated(queryClient),
  });
}
