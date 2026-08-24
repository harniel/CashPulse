import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "./api";

export function useHouseholds() {
  return useQuery({ queryKey: ["households"], queryFn: api.fetchHouseholds });
}

export function useHouseholdMembers(householdId: string | null) {
  return useQuery({
    queryKey: ["households", householdId, "members"],
    queryFn: () => api.fetchMembers(householdId as string),
    enabled: householdId !== null,
  });
}

export function useCreateHousehold() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createHousehold,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["households"] });
    },
  });
}

export function useLeaveHousehold() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.leaveHousehold,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["households"] });
    },
  });
}
