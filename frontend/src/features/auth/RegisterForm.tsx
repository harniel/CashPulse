import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { Alert, Box, Button, Link, Stack, TextField, Typography } from "@mui/material";

import { extractApiErrors } from "../../lib/apiErrors";
import { useRegister } from "./hooks";
import { registerSchema, type RegisterFormValues } from "./schemas";

export function RegisterForm() {
  const navigate = useNavigate();
  const registerUser = useRegister();
  const [topLevelError, setTopLevelError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = handleSubmit(async (values) => {
    setTopLevelError(null);
    try {
      await registerUser.mutateAsync(values);
      navigate("/", { replace: true });
    } catch (error) {
      const { fieldErrors, message } = extractApiErrors(error);
      for (const [field, msg] of Object.entries(fieldErrors)) {
        setError(field as keyof RegisterFormValues, { message: msg });
      }
      setTopLevelError(message);
    }
  });

  return (
    <Box component="form" onSubmit={onSubmit} noValidate>
      <Stack spacing={2}>
        <Typography variant="h5" component="h1">
          Create your account
        </Typography>
        {topLevelError && <Alert severity="error">{topLevelError}</Alert>}
        <Stack direction="row" spacing={2}>
          <TextField
            label="First name"
            autoComplete="given-name"
            fullWidth
            {...register("first_name")}
            error={!!errors.first_name}
            helperText={errors.first_name?.message}
          />
          <TextField
            label="Last name"
            autoComplete="family-name"
            fullWidth
            {...register("last_name")}
            error={!!errors.last_name}
            helperText={errors.last_name?.message}
          />
        </Stack>
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          {...register("email")}
          error={!!errors.email}
          helperText={errors.email?.message}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          {...register("password")}
          error={!!errors.password}
          helperText={errors.password?.message}
        />
        <Button type="submit" variant="contained" disabled={isSubmitting}>
          Sign up
        </Button>
        <Typography variant="body2">
          Already have an account? <Link component={RouterLink} to="/login">Log in</Link>
        </Typography>
      </Stack>
    </Box>
  );
}
