import { z } from "zod";

export const accountSchema = z.object({
  name: z.string().min(1, "Name is required"),
  account_type: z.enum(["cash", "bank", "e_wallet", "credit_card", "savings", "loan", "investment"]),
  currency: z
    .string()
    .length(3, "Use a 3-letter currency code (e.g. PHP)")
    .toUpperCase(),
  institution: z.string().optional(),
});
export type AccountFormValues = z.infer<typeof accountSchema>;
