import { z } from "zod";

// Shapes mirror what the DRF serializers enforce server-side — duplicated
// by necessity (client and server validate independently) but kept
// adjacent in code so drift is easy to spot (BLUEPRINT.md §12).

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
});
export type RegisterFormValues = z.infer<typeof registerSchema>;
