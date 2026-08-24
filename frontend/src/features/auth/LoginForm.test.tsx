import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import { renderWithProviders } from "../../testUtils";
import { LoginForm } from "./LoginForm";

const server = setupServer(
  http.post("http://localhost:8000/api/auth/login/", async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (body.email === "good@example.com" && body.password === "correct-password") {
      return HttpResponse.json({
        access: "fake-access-token",
        user: {
          id: "1",
          email: "good@example.com",
          first_name: "Good",
          last_name: "User",
          date_joined: "2026-01-01T00:00:00Z",
        },
      });
    }
    return HttpResponse.json({ detail: "Invalid email or password." }, { status: 401 });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("LoginForm", () => {
  it("shows a validation error instead of submitting when the email is empty", async () => {
    renderWithProviders(<LoginForm />);

    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument();
  });

  it("shows the server's error message on invalid credentials", async () => {
    renderWithProviders(<LoginForm />);

    await userEvent.type(screen.getByLabelText("Email"), "bad@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("Invalid email or password.")).toBeInTheDocument();
  });

  it("clears the error and succeeds with correct credentials", async () => {
    const { store } = renderWithProviders(<LoginForm />);

    await userEvent.type(screen.getByLabelText("Email"), "good@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "correct-password");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() => {
      expect(store.getState().session.user?.email).toBe("good@example.com");
    });
    expect(screen.queryByText("Invalid email or password.")).not.toBeInTheDocument();
  });
});
