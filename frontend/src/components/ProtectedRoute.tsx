import { Box, CircularProgress } from "@mui/material";
import { Navigate, Outlet } from "react-router-dom";

import { useBootstrapSession } from "../features/auth/hooks";
import { useCurrentUser } from "../hooks/useCurrentUser";

export function ProtectedRoute() {
  const { isLoading } = useBootstrapSession();
  const user = useCurrentUser();

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
