import { z } from "zod";

export const categorySchema = z.object({
  name: z.string().min(1, "Name is required"),
  kind: z.enum(["income", "expense"]),
  parent: z.string().nullable().optional(),
});
export type CategoryFormValues = z.infer<typeof categorySchema>;
