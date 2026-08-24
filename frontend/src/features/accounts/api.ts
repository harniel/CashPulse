import { client } from "../../api/client";
import type { PaginatedResponse } from "../../types";
import type { Account, AccountPayload } from "./types";

export function fetchAccounts(): Promise<Account[]> {
  return client.get<PaginatedResponse<Account>>("/accounts/").then((r) => r.data.results);
}

export function createAccount(payload: AccountPayload): Promise<Account> {
  return client.post<Account>("/accounts/", payload).then((r) => r.data);
}

export function updateAccount(id: string, payload: Partial<AccountPayload>): Promise<Account> {
  return client.patch<Account>(`/accounts/${id}/`, payload).then((r) => r.data);
}

export function deleteAccount(id: string): Promise<void> {
  return client.delete(`/accounts/${id}/`).then(() => undefined);
}
