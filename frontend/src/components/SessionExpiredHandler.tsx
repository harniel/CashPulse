import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useAppDispatch } from "../app/hooks";
import { setUser } from "../app/sessionSlice";
import { setSessionExpiredHandler } from "../api/client";

/** Renders nothing — just wires the axios interceptor's "refresh failed"
 * callback (client.ts) to clearing the session and bouncing to /login.
 * Needs to live inside <BrowserRouter> for useNavigate. */
export function SessionExpiredHandler() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  useEffect(() => {
    setSessionExpiredHandler(() => {
      dispatch(setUser(null));
      navigate("/login", { replace: true });
    });
    return () => setSessionExpiredHandler(null);
  }, [navigate, dispatch]);

  return null;
}
