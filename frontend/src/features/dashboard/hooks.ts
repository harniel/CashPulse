import { useQuery } from "@tanstack/react-query";

import * as api from "./api";

export function useDashboardSummary(householdId: string | null) {
  return useQuery({
    queryKey: ["dashboard", "summary", householdId],
    queryFn: () => api.fetchDashboardSummary(householdId),
  });
}
