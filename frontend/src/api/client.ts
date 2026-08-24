import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { getAccessToken, setAccessToken } from "./tokenStore";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

// Endpoints that either don't need an access token or ARE the refresh
// mechanism itself — a 401 from these must never trigger another refresh
// attempt (that would recurse or refresh over a login that just failed).
const SKIP_REFRESH_PATHS = ["/auth/login/", "/auth/register/", "/auth/refresh/"];

export const client = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // sends/receives the httpOnly refresh cookie
});

// A separate instance for the refresh call itself, so it never passes
// through the response interceptor below (a failed refresh must not
// trigger another refresh attempt).
const refreshClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

client.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

// Concurrent 401s (several queries in flight when the access token
// expires) must share one refresh call, not fire one each.
let refreshPromise: Promise<string> | null = null;

function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = refreshClient
      .post<{ access: string }>("/auth/refresh/")
      .then((response) => {
        setAccessToken(response.data.access);
        return response.data.access;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

let onSessionExpired: (() => void) | null = null;
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    const status = error.response?.status;
    const skipRefresh = SKIP_REFRESH_PATHS.some((path) => config?.url?.includes(path));

    if (status === 401 && config && !config._retried && !skipRefresh) {
      config._retried = true;
      try {
        const newToken = await refreshAccessToken();
        config.headers = config.headers ?? {};
        config.headers.Authorization = `Bearer ${newToken}`;
        return client(config);
      } catch (refreshError) {
        setAccessToken(null);
        onSessionExpired?.();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);
