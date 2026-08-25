import { z } from "zod";

export const budgetSchema = z.object({
  household: z.string().nullable().optional(),
  category: z.string().min(1, "Category is required"),
  month: z.string().min(1, "Month is required"), // "YYYY-MM" from an <input type="month">
  amount: z
    .string()
    .min(1, "Amount is required")
    .refine((v) => !Number.isNaN(Number(v)) && Number(v) > 0, "Amount must be greater than zero"),
});
export type BudgetFormValues = z.infer<typeof budgetSchema>;
