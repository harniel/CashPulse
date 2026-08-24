import type { AxiosError } from "axios";

import type { ApiErrorShape } from "../types";

interface ExtractedErrors {
  fieldErrors: Record<string, string>;
  message: string | null;
}

/** The one error adapter BLUEPRINT.md §10 calls for — DRF's default
 * {field: [messages]} shape is the only shape the whole API ever returns. */
export function extractApiErrors(error: unknown): ExtractedErrors {
  const axiosError = error as AxiosError<ApiErrorShape>;
  const data = axiosError?.response?.data;

  if (!data || typeof data !== "object") {
    return { fieldErrors: {}, message: "Something went wrong. Please try again." };
  }

  const fieldErrors: Record<string, string> = {};
  let message: string | null = null;

  for (const [key, value] of Object.entries(data)) {
    const text = Array.isArray(value) ? value.join(" ") : String(value);
    if (key === "detail" || key === "non_field_errors" || key === "__all__") {
      message = text;
    } else {
      fieldErrors[key] = text;
    }
  }

  return { fieldErrors, message };
}
