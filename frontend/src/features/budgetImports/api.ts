import { client } from "../../api/client";
import type {
  BudgetImportBatch,
  BudgetImportRow,
  ConfirmBudgetImportResult,
} from "./types";

export function uploadBudgetImport(file: File): Promise<BudgetImportBatch> {
  const formData = new FormData();
  formData.append("file", file);
  return client
    .post<BudgetImportBatch>("/imports/budgets/", formData)
    .then((r) => r.data);
}

export function fetchBudgetImportPreview(batchId: string): Promise<BudgetImportRow[]> {
  return client.get<BudgetImportRow[]>(`/imports/budgets/${batchId}/preview/`).then((r) => r.data);
}

export function confirmBudgetImport(
  batchId: string,
  rowIds: string[],
): Promise<ConfirmBudgetImportResult> {
  return client
    .post<ConfirmBudgetImportResult>(`/imports/budgets/${batchId}/confirm/`, { row_ids: rowIds })
    .then((r) => r.data);
}

export async function downloadBudgetImportTemplate(): Promise<void> {
  const response = await client.get("/imports/budgets/template/", { responseType: "blob" });
  const url = URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "budget_import_template.xlsx";
  link.click();
  URL.revokeObjectURL(url);
}
