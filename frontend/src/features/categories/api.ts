import type { AxiosResponse } from "axios";

import { client } from "../../api/client";
import type { PaginatedResponse } from "../../types";
import type { Category, CategoryPayload } from "./types";

export async function fetchCategories(): Promise<Category[]> {
  // The seed data alone is ~29 system categories — already past the
  // API's default page size (25) — so this one list actually needs to
  // follow pagination, unlike the other (much shorter) lists in this app.
  let url: string | null = "/categories/";
  let results: Category[] = [];
  while (url) {
    const response: AxiosResponse<PaginatedResponse<Category>> = await client.get(url);
    results = results.concat(response.data.results);
    url = response.data.next;
  }
  return results;
}

export function createCategory(payload: CategoryPayload): Promise<Category> {
  return client.post<Category>("/categories/", payload).then((r) => r.data);
}

export function deleteCategory(id: string): Promise<void> {
  return client.delete(`/categories/${id}/`).then(() => undefined);
}
