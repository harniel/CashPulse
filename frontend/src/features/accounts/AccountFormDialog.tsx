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

import { extractApiErrors } from "../../lib/apiErrors";
import { useCreateAccount, useUpdateAccount } from "./hooks";
import { accountSchema, type AccountFormValues } from "./schemas";
import { ACCOUNT_TYPE_LABELS, type Account } from "./types";

interface Props {
  open: boolean;
  onClose: () => void;
  /** When set, the dialog edits this account instead of creating a new one. */
  account?: Account;
}

const DEFAULT_VALUES: AccountFormValues = {
  name: "",
  account_type: "bank",
  currency: "PHP",
  institution: "",
};

export function AccountFormDialog({ open, onClose, account }: Props) {
  const isEditing = !!account;
  const createAccount = useCreateAccount();
  const updateAccount = useUpdateAccount();
  const [topLevelError, setTopLevelError] = useState<string | null>(null);

  const {
    control,
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<AccountFormValues>({
    resolver: zodResolver(accountSchema),
    defaultValues: DEFAULT_VALUES,
  });

  useEffect(() => {
    if (open) {
      reset(
        account
          ? {
              name: account.name,
              account_type: account.account_type,
              currency: account.currency,
              institution: account.institution,
            }
          : DEFAULT_VALUES,
      );
      setTopLevelError(null);
    }
  }, [open, account, reset]);

  const onSubmit = handleSubmit(async (values) => {
    setTopLevelError(null);
    try {
      if (isEditing) {
        await updateAccount.mutateAsync({ id: account.id, payload: values });
      } else {
        await createAccount.mutateAsync(values);
      }
      onClose();
    } catch (error) {
      const { fieldErrors, message } = extractApiErrors(error);
      for (const [field, msg] of Object.entries(fieldErrors)) {
        setError(field as keyof AccountFormValues, { message: msg });
      }
      setTopLevelError(message);
    }
  });

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{isEditing ? "Edit account" : "New account"}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {topLevelError && <Alert severity="error">{topLevelError}</Alert>}
          <TextField
            label="Name"
            autoFocus
            fullWidth
            {...register("name")}
            error={!!errors.name}
            helperText={errors.name?.message}
          />
          <Controller
            name="account_type"
            control={control}
            render={({ field }) => (
              <TextField {...field} select label="Type" fullWidth>
                {Object.entries(ACCOUNT_TYPE_LABELS).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />
          <TextField
            label="Currency"
            fullWidth
            {...register("currency")}
            error={!!errors.currency}
            helperText={errors.currency?.message ?? "3-letter code, e.g. PHP, USD"}
          />
          <TextField
            label="Institution (optional)"
            fullWidth
            {...register("institution")}
            error={!!errors.institution}
            helperText={errors.institution?.message}
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
