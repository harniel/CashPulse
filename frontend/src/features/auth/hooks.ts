import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAppDispatch } from "../../app/hooks";
import { setUser } from "../../app/sessionSlice";
import * as api from "../../api/auth";
import { setAccessToken } from "../../api/tokenStore";

export function useLogin() {
  const dispatch = useAppDispatch();
  return useMutation({
    mutationFn: api.login,
    onSuccess: (data) => {
      setAccessToken(data.access);
      dispatch(setUser(data.user));
    },
  });
}

export function useRegister() {
  const dispatch = useAppDispatch();
  return useMutation({
    mutationFn: api.register,
    onSuccess: (data) => {
      setAccessToken(data.access);
      dispatch(setUser(data.user));
    },
  });
}

export function useLogout() {
  const dispatch = useAppDispatch();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.logout,
    onSettled: () => {
      setAccessToken(null);
      dispatch(setUser(null));
      queryClient.clear();
    },
  });
}

/**
 * Runs once at app boot. There's no access token in memory yet after a
 * fresh page load, so this request 401s immediately and the axios
 * interceptor (client.ts) transparently tries a refresh using the
 * httpOnly cookie — succeeding silently restores the session, failing
 * just leaves the user logged out. Either way this resolves without the
 * caller needing to know which happened.
 */
export function useBootstrapSession() {
  const dispatch = useAppDispatch();
  return useQuery({
    queryKey: ["session", "bootstrap"],
    queryFn: async () => {
      try {
        const user = await api.fetchCurrentUser();
        dispatch(setUser(user));
        return user;
      } catch (error) {
        dispatch(setUser(null));
        throw error;
      }
    },
    retry: false,
    staleTime: Infinity,
  });
}
