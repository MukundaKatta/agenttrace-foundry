"""Cost calculator tests."""

import pytest

from agenttrace_foundry.cost import DEFAULT_PRICES, ModelPrice, cost_usd, total_cost


def test_cost_usd_basic_arithmetic() -> None:
    # 1M input + 1M output at default mini rates: $0.50 + $2.00 = $2.50
    price = ModelPrice(input_per_million=0.50, output_per_million=2.00)
    cost = cost_usd(
        "x",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        prices={"x": price},
    )
    assert cost == pytest.approx(2.50)


def test_cost_usd_with_cache_hits_uses_cached_rate() -> None:
    price = ModelPrice(
        input_per_million=1.0,
        output_per_million=0.0,
        cached_input_per_million=0.10,
    )
    # 1M input, of which 500k are cached. Bill 500k at $1/M plus 500k at $0.10/M.
    cost = cost_usd(
        "x",
        input_tokens=1_000_000,
        output_tokens=0,
        cached_input_tokens=500_000,
        prices={"x": price},
    )
    assert cost == pytest.approx(0.55)


def test_cost_usd_unknown_model_raises() -> None:
    with pytest.raises(KeyError):
        cost_usd("nope", 100, 100)


def test_total_cost_sums_records() -> None:
    records = [
        {"model": "foundry-fast", "input_tokens": 1000, "output_tokens": 0},
        {"model": "foundry-fast", "input_tokens": 0, "output_tokens": 1000},
    ]
    expected = (
        1000 * DEFAULT_PRICES["foundry-fast"].input_per_million / 1_000_000
        + 1000 * DEFAULT_PRICES["foundry-fast"].output_per_million / 1_000_000
    )
    assert total_cost(records) == pytest.approx(expected)
