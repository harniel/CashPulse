import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "./api";
import type { BudgetPayload } from "./types";

const BUDGETS_KEY = ["budgets"];

export function useBudgets(month: string, householdId: string | null) {
  return useQuery({
    queryKey: [...BUDGETS_KEY, month, householdId],
    queryFn: async () => {
      if (householdId) {
        return api.fetchBudgets({ month, household: householdId });
      }
      // No is_shared filter on this endpoint — fetch everything in scope
      // and keep only the personal (household === null) rows client-side.
      const all = await api.fetchBudgets({ month });
      return all.filter((b) => b.household === null);
    },
  });
}

export function useBudgetPerformance(id: string | null) {
  return useQuery({
    queryKey: [...BUDGETS_KEY, id, "performance"],
    queryFn: () => api.fetchBudgetPerformance(id as string),
    enabled: id !== null,
  });
}

function invalidateBudgetRelated(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: BUDGETS_KEY });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useCreateBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createBudget,
    onSuccess: () => invalidateBudgetRelated(queryClient),
  });
}

export function useUpdateBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<BudgetPayload> }) =>
      api.updateBudget(id, payload),
    onSuccess: () => invalidateBudgetRelated(queryClient),
  });
}

export function useDeleteBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteBudget,
    onSuccess: () => invalidateBudgetRelated(queryClient),
  });
}
