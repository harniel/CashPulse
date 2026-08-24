import { describe, expect, it } from "vitest";

import { transactionSchema } from "./schemas";

const base = {
  household: null,
  account: "acc-1",
  amount: "50.00",
  date: "2026-08-24",
  description: "",
};

describe("transactionSchema", () => {
  it("accepts a valid expense with a category", () => {
    const result = transactionSchema.safeParse({
      ...base,
      type: "expense",
      category: "cat-1",
      to_account: null,
    });
    expect(result.success).toBe(true);
  });

  it("rejects an expense with no category", () => {
    const result = transactionSchema.safeParse({
      ...base,
      type: "expense",
      category: null,
      to_account: null,
    });
    expect(result.success).toBe(false);
  });

  it("rejects a transfer with no destination account", () => {
    const result = transactionSchema.safeParse({
      ...base,
      type: "transfer",
      category: null,
      to_account: null,
    });
    expect(result.success).toBe(false);
  });

  it("rejects a transfer whose destination matches the source account", () => {
    const result = transactionSchema.safeParse({
      ...base,
      type: "transfer",
      category: null,
      to_account: "acc-1",
    });
    expect(result.success).toBe(false);
  });

  it("accepts a valid transfer to a different account", () => {
    const result = transactionSchema.safeParse({
      ...base,
      type: "transfer",
      category: null,
      to_account: "acc-2",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a non-positive amount", () => {
    const result = transactionSchema.safeParse({
      ...base,
      type: "expense",
      category: "cat-1",
      to_account: null,
      amount: "0",
    });
    expect(result.success).toBe(false);
  });
});
