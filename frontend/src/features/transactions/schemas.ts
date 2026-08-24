import { z } from "zod";

// Mirrors Transaction.clean() / TransactionSerializer.validate() server-side
// (BLUEPRINT.md §8/§10) — transfer needs a different destination account and
// no category; income/expense need a category and no destination account.
export const transactionSchema = z
  .object({
    household: z.string().nullable().optional(),
    type: z.enum(["income", "expense", "transfer"]),
    account: z.string().min(1, "Account is required"),
    to_account: z.string().nullable().optional(),
    category: z.string().nullable().optional(),
    amount: z
      .string()
      .min(1, "Amount is required")
      .refine((v) => !Number.isNaN(Number(v)) && Number(v) > 0, "Amount must be greater than zero"),
    date: z.string().min(1, "Date is required"),
    description: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.type === "transfer") {
      if (!data.to_account) {
        ctx.addIssue({
          code: "custom",
          path: ["to_account"],
          message: "Destination account is required for transfers",
        });
      } else if (data.to_account === data.account) {
        ctx.addIssue({
          code: "custom",
          path: ["to_account"],
          message: "Must differ from the source account",
        });
      }
    } else if (!data.category) {
      ctx.addIssue({ code: "custom", path: ["category"], message: "Category is required" });
    }
  });

export type TransactionFormValues = z.infer<typeof transactionSchema>;
