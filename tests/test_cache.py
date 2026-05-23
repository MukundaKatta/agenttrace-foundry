"""Cache-stats tests."""

import pytest

from agenttrace_foundry.cache import cache_stats


def test_cache_stats_empty() -> None:
    stats = cache_stats([])
    assert stats.total_calls == 0
    assert stats.cache_hits == 0
    assert stats.hit_ratio == 0.0
    assert stats.cached_input_tokens == 0
    assert stats.uncached_input_tokens == 0


def test_cache_stats_counts_hits_and_tokens() -> None:
    records = [
        {"cache_hit": True, "input_tokens": 1000, "cached_input_tokens": 800},
        {"cache_hit": False, "input_tokens": 400, "cached_input_tokens": 0},
        {"cache_hit": True, "input_tokens": 500, "cached_input_tokens": 300},
    ]
    stats = cache_stats(records)
    assert stats.total_calls == 3
    assert stats.cache_hits == 2
    assert stats.hit_ratio == pytest.approx(2 / 3)
    assert stats.cached_input_tokens == 1100
    # Uncached = 200 (first) + 400 (second) + 200 (third) = 800
    assert stats.uncached_input_tokens == 800
