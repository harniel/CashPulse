import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Testing Library's automatic cleanup only self-registers when Vitest's
// globals are enabled (vite.config.ts deliberately keeps globals: false,
// so every test file's imports stay explicit) — so it's done by hand here.
afterEach(() => {
  cleanup();
});
