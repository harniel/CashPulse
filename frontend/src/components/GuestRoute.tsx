import { Navigate, Outlet } from "react-router-dom";

import { useBootstrapSession } from "../features/auth/hooks";
import { useCurrentUser } from "../hooks/useCurrentUser";

/** The inverse of ProtectedRoute — keeps an already-logged-in user off
 * /login and /register. */
export function GuestRoute() {
  const { isLoading } = useBootstrapSession();
  const user = useCurrentUser();

  if (isLoading) {
    return null;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
