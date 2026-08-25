import { client } from "../../api/client";
import type { DashboardSummary } from "./types";

export function fetchDashboardSummary(householdId: string | null): Promise<DashboardSummary> {
  const params = householdId ? { household: householdId } : {};
  return client.get<DashboardSummary>("/dashboard/summary/", { params }).then((r) => r.data);
}
