import type { ISODateTime } from "../../types";

export type CategoryKind = "income" | "expense";

export interface Category {
  id: string;
  name: string;
  kind: CategoryKind;
  parent: string | null;
  is_system: boolean;
  created_at: ISODateTime;
}

export interface CategoryPayload {
  name: string;
  kind: CategoryKind;
  parent?: string | null;
}
