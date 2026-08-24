import type { User } from "../types";
import { client } from "./client";

export interface AuthResponse {
  access: string;
  user: User;
}

export interface RegisterPayload {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export function register(data: RegisterPayload): Promise<AuthResponse> {
  return client.post<AuthResponse>("/auth/register/", data).then((r) => r.data);
}

export function login(data: LoginPayload): Promise<AuthResponse> {
  return client.post<AuthResponse>("/auth/login/", data).then((r) => r.data);
}

export function logout(): Promise<void> {
  return client.post("/auth/logout/").then(() => undefined);
}

export function fetchCurrentUser(): Promise<User> {
  return client.get<User>("/auth/me/").then((r) => r.data);
}
