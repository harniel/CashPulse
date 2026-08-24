import { useMemo, useState } from "react";
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
import { useCategories, useCreateCategory } from "./hooks";
import { categorySchema, type CategoryFormValues } from "./schemas";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Preselects + locks the kind when opened from an income/expense-specific "Add" button. */
  defaultKind?: "income" | "expense";
}

export function CreateCategoryDialog({ open, onClose, defaultKind }: Props) {
  const { data: categories = [] } = useCategories();
  const createCategory = useCreateCategory();
  const [topLevelError, setTopLevelError] = useState<string | null>(null);

  const {
    control,
    register,
    handleSubmit,
    watch,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CategoryFormValues>({
    resolver: zodResolver(categorySchema),
    defaultValues: { name: "", kind: defaultKind ?? "expense", parent: null },
  });

  const kind = watch("kind");
  const topLevelOptions = useMemo(
    () => categories.filter((c) => c.parent === null && c.kind === kind),
    [categories, kind],
  );

  const handleClose = () => {
    reset({ name: "", kind: defaultKind ?? "expense", parent: null });
    setTopLevelError(null);
    onClose();
  };

  const onSubmit = handleSubmit(async (values) => {
    setTopLevelError(null);
    try {
      await createCategory.mutateAsync({ ...values, parent: values.parent || null });
      handleClose();
    } catch (error) {
      const { fieldErrors, message } = extractApiErrors(error);
      for (const [field, msg] of Object.entries(fieldErrors)) {
        setError(field as keyof CategoryFormValues, { message: msg });
      }
      setTopLevelError(message);
    }
  });

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="xs">
      <DialogTitle>New category</DialogTitle>
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
            name="kind"
            control={control}
            render={({ field }) => (
              <TextField {...field} select label="Kind" fullWidth disabled={!!defaultKind}>
                <MenuItem value="expense">Expense</MenuItem>
                <MenuItem value="income">Income</MenuItem>
              </TextField>
            )}
          />
          <Controller
            name="parent"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                value={field.value ?? ""}
                select
                label="Parent category (optional)"
                fullWidth
                helperText="Leave blank for a top-level category"
              >
                <MenuItem value="">
                  <em>None — top-level</em>
                </MenuItem>
                {topLevelOptions.map((category) => (
                  <MenuItem key={category.id} value={category.id}>
                    {category.name}
                    {category.is_system ? " (system)" : ""}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button variant="contained" onClick={onSubmit} disabled={isSubmitting}>
          Create
        </Button>
      </DialogActions>
    </Dialog>
  );
}
