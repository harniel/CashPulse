import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { User } from "../types";

interface SessionState {
  user: User | null;
  /** The one piece of state that's genuinely global and non-derivable
   * (BLUEPRINT.md §12) — almost every query needs it, and it isn't
   * "owned" by any single feature. */
  activeHouseholdId: string | null;
}

const initialState: SessionState = {
  user: null,
  activeHouseholdId: null,
};

const sessionSlice = createSlice({
  name: "session",
  initialState,
  reducers: {
    setUser(state, action: PayloadAction<User | null>) {
      state.user = action.payload;
      if (action.payload === null) {
        state.activeHouseholdId = null;
      }
    },
    setActiveHousehold(state, action: PayloadAction<string | null>) {
      state.activeHouseholdId = action.payload;
    },
  },
});

export const { setUser, setActiveHousehold } = sessionSlice.actions;
export default sessionSlice.reducer;
