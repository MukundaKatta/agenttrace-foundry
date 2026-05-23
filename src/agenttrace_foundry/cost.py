"""Cost calculator for Foundry-hosted models.

Mirrors the shape of the user's claude-cost / bedrock-cost crates: a small
per-model price table plus a function that turns token counts into dollars.

Prices below are illustrative defaults. Override with your own table when you
plug into real Foundry pricing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    """Per-million-token USD price for a single model."""

    input_per_million: float
    output_per_million: float
    cached_input_per_million: float = 0.0


# Defaults are placeholders. Swap in real Foundry pricing in production.
DEFAULT_PRICES: dict[str, ModelPrice] = {
    "foundry-reasoning-pro": ModelPrice(3.0, 15.0, 0.30),
    "foundry-reasoning-mini": ModelPrice(0.50, 2.00, 0.05),
    "foundry-fast": ModelPrice(0.15, 0.60, 0.015),
}


def cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    prices: dict[str, ModelPrice] | None = None,
) -> float:
    """Compute the USD cost for a single model call.

    Cached input tokens are billed at the cached rate and excluded from the
    standard input bucket. Unknown models raise KeyError on purpose so callers
    notice missing price entries instead of silently zeroing cost.
    """

    table = prices if prices is not None else DEFAULT_PRICES
    price = table[model]
    billable_input = max(input_tokens - cached_input_tokens, 0)
    return (
        billable_input * price.input_per_million / 1_000_000.0
        + cached_input_tokens * price.cached_input_per_million / 1_000_000.0
        + output_tokens * price.output_per_million / 1_000_000.0
    )


def total_cost(records: list[dict], prices: dict[str, ModelPrice] | None = None) -> float:
    """Sum cost across a list of call records.

    Each record needs `model`, `input_tokens`, `output_tokens`, and optionally
    `cached_input_tokens`.
    """

    total = 0.0
    for record in records:
        total += cost_usd(
            record["model"],
            record["input_tokens"],
            record["output_tokens"],
            record.get("cached_input_tokens", 0),
            prices,
        )
    return total
