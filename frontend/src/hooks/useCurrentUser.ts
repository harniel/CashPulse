import { useAppSelector } from "../app/hooks";

export function useCurrentUser() {
  return useAppSelector((state) => state.session.user);
}
