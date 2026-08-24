import { useAppDispatch, useAppSelector } from "../app/hooks";
import { setActiveHousehold } from "../app/sessionSlice";

export function useActiveHousehold() {
  const activeHouseholdId = useAppSelector((state) => state.session.activeHouseholdId);
  const dispatch = useAppDispatch();

  return {
    activeHouseholdId,
    setActiveHouseholdId: (id: string | null) => dispatch(setActiveHousehold(id)),
  };
}
