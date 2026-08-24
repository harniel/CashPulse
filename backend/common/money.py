from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")


def quantize(amount):
    """Round a Decimal to 2 places, half-up — the one place this happens (Section 14)."""
    return Decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
