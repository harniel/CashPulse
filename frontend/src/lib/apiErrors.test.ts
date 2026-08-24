import { describe, expect, it } from "vitest";

import { extractApiErrors } from "./apiErrors";

describe("extractApiErrors", () => {
  it("separates field errors from a top-level detail message", () => {
    const error = {
      response: {
        data: {
          email: ["This field is required."],
          detail: "Something else went wrong.",
        },
      },
    };

    const { fieldErrors, message } = extractApiErrors(error);

    expect(fieldErrors).toEqual({ email: "This field is required." });
    expect(message).toBe("Something else went wrong.");
  });

  it("joins multiple messages for the same field", () => {
    const error = {
      response: { data: { password: ["Too short.", "Too common."] } },
    };

    const { fieldErrors } = extractApiErrors(error);

    expect(fieldErrors.password).toBe("Too short. Too common.");
  });

  it("falls back to a generic message when there's no response data", () => {
    const { fieldErrors, message } = extractApiErrors(new Error("network down"));

    expect(fieldErrors).toEqual({});
    expect(message).toBe("Something went wrong. Please try again.");
  });
});
