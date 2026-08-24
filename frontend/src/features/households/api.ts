import { client } from "../../api/client";
import type { PaginatedResponse } from "../../types";
import type { Household, HouseholdMembership } from "./types";

export function fetchHouseholds(): Promise<Household[]> {
  return client.get<PaginatedResponse<Household>>("/households/").then((r) => r.data.results);
}

export function createHousehold(name: string): Promise<Household> {
  return client.post<Household>("/households/", { name }).then((r) => r.data);
}

export function fetchMembers(householdId: string): Promise<HouseholdMembership[]> {
  return client.get<HouseholdMembership[]>(`/households/${householdId}/members/`).then((r) => r.data);
}

export function leaveHousehold(householdId: string): Promise<void> {
  return client.post(`/households/${householdId}/leave/`).then(() => undefined);
}
