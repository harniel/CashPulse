import { configureStore } from "@reduxjs/toolkit";

import sessionReducer from "./sessionSlice";

export function createStore() {
  return configureStore({
    reducer: {
      session: sessionReducer,
    },
  });
}

export const store = createStore();

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
