import type { Money } from "../types";

/** DRF DecimalFields arrive as strings — always format through here
 * rather than displaying the raw string or doing ad-hoc Number() calls. */
export function formatMoney(amount: Money, currency = "PHP"): string {
  const value = Number(amount);
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value);
  } catch {
    // Intl throws on a currency code it doesn't recognize — fall back to
    // a plain number rather than letting the whole page crash over it.
    return `${currency} ${value.toFixed(2)}`;
  }
}
