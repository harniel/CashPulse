import { useEffect, useMemo, useState } from "react";
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

import { useAccounts } from "../accounts/hooks";
import { useCategories } from "../categories/hooks";
import { useHouseholds } from "../households/hooks";
import { extractApiErrors } from "../../lib/apiErrors";
import { useCreateTransaction, useUpdateTransaction } from "./hooks";
import { transactionSchema, type TransactionFormValues } from "./schemas";
import type { Transaction } from "./types";

interface Props {
  open: boolean;
  onClose: () => void;
  transaction?: Transaction;
  /** Preselects household when creating from a household-scoped view. */
  defaultHouseholdId?: string | null;
}

function defaultValues(defaultHouseholdId?: string | null): TransactionFormValues {
  return {
    household: defaultHouseholdId ?? null,
    type: "expense",
    account: "",
    to_account: null,
    category: null,
    amount: "",
    date: new Date().toISOString().slice(0, 10),
    description: "",
  };
}

export function TransactionFormDialog({ open, onClose, transaction, defaultHouseholdId }: Props) {
  const isEditing = !!transaction;
  const { data: accounts = [] } = useAccounts();
  const { data: categories = [] } = useCategories();
  const { data: households = [] } = useHouseholds();
  const createTransaction = useCreateTransaction();
  const updateTransaction = useUpdateTransaction();
  const [topLevelError, setTopLevelError] = useState<string | null>(null);

  const {
    control,
    register,
    handleSubmit,
    watch,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<TransactionFormValues>({
    resolver: zodResolver(transactionSchema),
    defaultValues: defaultValues(defaultHouseholdId),
  });

  useEffect(() => {
    if (open) {
      reset(
        transaction
          ? {
              household: transaction.household,
              type: transaction.type,
              account: transaction.account,
              to_account: transaction.to_account,
              category: transaction.category,
              amount: transaction.amount,
              date: transaction.date,
              description: transaction.description,
            }
          : defaultValues(defaultHouseholdId),
      );
      setTopLevelError(null);
    }
  }, [open, transaction, defaultHouseholdId, reset]);

  const type = watch("type");
  const account = watch("account");

  const categoryOptions = useMemo(
    () =>
      categories
        .filter((c) => c.kind === type)
        .map((c) => {
          const parent = c.parent ? categories.find((p) => p.id === c.parent) : null;
          return { id: c.id, label: parent ? `${parent.name} > ${c.name}` : c.name };
        }),
    [categories, type],
  );

  const toAccountOptions = useMemo(() => accounts.filter((a) => a.id !== account), [accounts, account]);

  const onSubmit = handleSubmit(async (values) => {
    setTopLevelError(null);
    const payload = {
      ...values,
      household: values.household || null,
      to_account: values.type === "transfer" ? values.to_account : null,
      category: values.type === "transfer" ? null : values.category,
    };
    try {
      if (isEditing) {
        await updateTransaction.mutateAsync({ id: transaction.id, payload });
      } else {
        await createTransaction.mutateAsync(payload);
      }
      onClose();
    } catch (error) {
      const { fieldErrors, message } = extractApiErrors(error);
      for (const [field, msg] of Object.entries(fieldErrors)) {
        setError(field as keyof TransactionFormValues, { message: msg });
      }
      setTopLevelError(message);
    }
  });

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{isEditing ? "Edit transaction" : "New transaction"}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {topLevelError && <Alert severity="error">{topLevelError}</Alert>}

          <Controller
            name="type"
            control={control}
            render={({ field }) => (
              <TextField {...field} select label="Type" fullWidth>
                <MenuItem value="expense">Expense</MenuItem>
                <MenuItem value="income">Income</MenuItem>
                <MenuItem value="transfer">Transfer</MenuItem>
              </TextField>
            )}
          />

          <Controller
            name="account"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                select
                label={type === "transfer" ? "From account" : "Account"}
                fullWidth
                error={!!errors.account}
                helperText={errors.account?.message}
              >
                {accounts.map((a) => (
                  <MenuItem key={a.id} value={a.id}>
                    {a.name}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />

          {type === "transfer" ? (
            <Controller
              name="to_account"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  value={field.value ?? ""}
                  select
                  label="To account"
                  fullWidth
                  error={!!errors.to_account}
                  helperText={errors.to_account?.message}
                >
                  {toAccountOptions.map((a) => (
                    <MenuItem key={a.id} value={a.id}>
                      {a.name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          ) : (
            <Controller
              name="category"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  value={field.value ?? ""}
                  select
                  label="Category"
                  fullWidth
                  error={!!errors.category}
                  helperText={errors.category?.message}
                >
                  {categoryOptions.map((c) => (
                    <MenuItem key={c.id} value={c.id}>
                      {c.label}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          )}

          <TextField
            label="Amount"
            fullWidth
            {...register("amount")}
            error={!!errors.amount}
            helperText={errors.amount?.message}
          />

          <TextField
            label="Date"
            type="date"
            fullWidth
            slotProps={{ inputLabel: { shrink: true } }}
            {...register("date")}
            error={!!errors.date}
            helperText={errors.date?.message}
          />

          <TextField label="Description" fullWidth {...register("description")} />

          <Controller
            name="household"
            control={control}
            render={({ field }) => (
              <TextField {...field} value={field.value ?? ""} select label="Share with" fullWidth>
                <MenuItem value="">Personal (just me)</MenuItem>
                {households.map((h) => (
                  <MenuItem key={h.id} value={h.id}>
                    {h.name}
                  </MenuItem>
                ))}
              </TextField>
            )}
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
