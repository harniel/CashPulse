import { describe, expect, it } from "vitest";

import { formatMoney } from "./money";

describe("formatMoney", () => {
  it("formats a PHP amount with the peso sign", () => {
    expect(formatMoney("1500.00", "PHP")).toBe("₱1,500.00");
  });

  it("formats a USD amount with the dollar sign", () => {
    expect(formatMoney("42.50", "USD")).toBe("$42.50");
  });

  it("falls back to a plain number for a malformed currency code", () => {
    // "XXX" is technically valid ISO 4217 ("no currency") and Intl accepts
    // it with a generic symbol — an actually malformed code (wrong length)
    // is what triggers Intl's RangeError and this function's fallback.
    expect(formatMoney("10.00", "TOOLONG")).toBe("TOOLONG 10.00");
  });
});
