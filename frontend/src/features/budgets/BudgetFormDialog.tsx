import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";

import { useCategories } from "../categories/hooks";
import { extractApiErrors } from "../../lib/apiErrors";
import { useCreateBudget, useUpdateBudget } from "./hooks";
import { budgetSchema, type BudgetFormValues } from "./schemas";
import type { Budget } from "./types";

interface Props {
  open: boolean;
  onClose: () => void;
  budget?: Budget;
  defaultMonth: string; // "YYYY-MM"
  defaultHouseholdId?: string | null;
}

export function BudgetFormDialog({ open, onClose, budget, defaultMonth, defaultHouseholdId }: Props) {
  const isEditing = !!budget;
  const { data: categories = [] } = useCategories();
  const expenseCategories = categories.filter((c) => c.kind === "expense");
  const createBudget = useCreateBudget();
  const updateBudget = useUpdateBudget();
  const [topLevelError, setTopLevelError] = useState<string | null>(null);

  const {
    control,
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<BudgetFormValues>({
    resolver: zodResolver(budgetSchema),
    defaultValues: { household: defaultHouseholdId ?? null, category: "", month: defaultMonth, amount: "" },
  });

  useEffect(() => {
    if (open) {
      reset(
        budget
          ? {
              household: budget.household,
              category: budget.category,
              month: budget.month.slice(0, 7),
              amount: budget.amount,
            }
          : { household: defaultHouseholdId ?? null, category: "", month: defaultMonth, amount: "" },
      );
      setTopLevelError(null);
    }
  }, [open, budget, defaultMonth, defaultHouseholdId, reset]);

  const onSubmit = handleSubmit(async (values) => {
    setTopLevelError(null);
    const payload = { ...values, month: `${values.month}-01`, household: values.household || null };
    try {
      if (isEditing) {
        await updateBudget.mutateAsync({ id: budget.id, payload });
      } else {
        await createBudget.mutateAsync(payload);
      }
      onClose();
    } catch (error) {
      const { fieldErrors, message } = extractApiErrors(error);
      for (const [field, msg] of Object.entries(fieldErrors)) {
        setError(field as keyof BudgetFormValues, { message: msg });
      }
      setTopLevelError(message);
    }
  });

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{isEditing ? "Edit budget" : "New budget"}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {topLevelError && <Alert severity="error">{topLevelError}</Alert>}
          <Controller
            name="category"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                select
                label="Category"
                fullWidth
                disabled={isEditing}
                error={!!errors.category}
                helperText={errors.category?.message}
              >
                {expenseCategories.map((c) => {
                  const parent = c.parent ? categories.find((p) => p.id === c.parent) : null;
                  return (
                    <MenuItem key={c.id} value={c.id}>
                      {parent ? `${parent.name} > ${c.name}` : c.name}
                    </MenuItem>
                  );
                })}
              </TextField>
            )}
          />
          <TextField
            label="Month"
            type="month"
            fullWidth
            disabled={isEditing}
            slotProps={{ inputLabel: { shrink: true } }}
            {...register("month")}
            error={!!errors.month}
            helperText={errors.month?.message}
          />
          <TextField
            label="Amount"
            fullWidth
            {...register("amount")}
            error={!!errors.amount}
            helperText={errors.amount?.message}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={onSubmit} disabled={isSubmitting}>
          {isEditing ? "Save" : "Create"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
