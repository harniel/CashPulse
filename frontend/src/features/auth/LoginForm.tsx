import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { Alert, Box, Button, Link, Stack, TextField, Typography } from "@mui/material";

import { extractApiErrors } from "../../lib/apiErrors";
import { useLogin } from "./hooks";
import { loginSchema, type LoginFormValues } from "./schemas";

export function LoginForm() {
  const navigate = useNavigate();
  const login = useLogin();
  const [topLevelError, setTopLevelError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const onSubmit = handleSubmit(async (values) => {
    setTopLevelError(null);
    try {
      await login.mutateAsync(values);
      navigate("/", { replace: true });
    } catch (error) {
      const { fieldErrors, message } = extractApiErrors(error);
      for (const [field, msg] of Object.entries(fieldErrors)) {
        setError(field as keyof LoginFormValues, { message: msg });
      }
      setTopLevelError(message ?? "Invalid email or password.");
    }
  });

  return (
    <Box component="form" onSubmit={onSubmit} noValidate>
      <Stack spacing={2}>
        <Typography variant="h5" component="h1">
          Log in
        </Typography>
        {topLevelError && <Alert severity="error">{topLevelError}</Alert>}
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
          autoComplete="current-password"
          {...register("password")}
          error={!!errors.password}
          helperText={errors.password?.message}
        />
        <Button type="submit" variant="contained" disabled={isSubmitting}>
          Log in
        </Button>
        <Typography variant="body2">
          Don&apos;t have an account? <Link component={RouterLink} to="/register">Sign up</Link>
        </Typography>
      </Stack>
    </Box>
  );
}
