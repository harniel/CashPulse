import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "./api";

export function useUploadBudgetImport() {
  return useMutation({ mutationFn: api.uploadBudgetImport });
}

export function useBudgetImportPreview(batchId: string | null) {
  return useQuery({
    queryKey: ["budgetImports", batchId, "preview"],
    queryFn: () => api.fetchBudgetImportPreview(batchId as string),
    enabled: batchId !== null,
  });
}

export function useConfirmBudgetImport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ batchId, rowIds }: { batchId: string; rowIds: string[] }) =>
      api.confirmBudgetImport(batchId, rowIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
