// Shared primitive types only — not a dumping ground (see BLUEPRINT.md §11).
// Feature-specific types live in each feature's own types.ts.

/** DRF DecimalFields serialize as strings, never numbers — parse with
 * Number()/parseFloat() only at the point of display/arithmetic. */
export type Money = string;

/** ISO 8601 date, e.g. "2026-08-24" (no time component). */
export type ISODate = string;

/** ISO 8601 datetime with timezone, e.g. "2026-08-24T10:00:00Z". */
export type ISODateTime = string;

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  date_joined: ISODateTime;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** DRF's default validation error shape: {field: [messages]} plus an
 * optional non-field "detail" or "__all__" (BLUEPRINT.md §10). */
export type ApiErrorShape = Record<string, string[] | string>;
