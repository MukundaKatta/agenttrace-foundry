"""Prompt-cache observability.

A tiny analog of the user's cachebench library. The harness records each call's
cache_hit flag and the cache module computes hit ratio plus the cost saving
implied by cached vs uncached tokens.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheStats:
    total_calls: int
    cache_hits: int
    hit_ratio: float
    cached_input_tokens: int
    uncached_input_tokens: int


def cache_stats(records: list[dict]) -> CacheStats:
    """Summarize cache usage across a list of call records.

    Each record needs `cache_hit` (bool), `input_tokens` (int), and
    `cached_input_tokens` (int, default 0). Cache ratio is 0.0 for an empty
    input.
    """

    total = len(records)
    hits = sum(1 for r in records if r.get("cache_hit"))
    cached = sum(r.get("cached_input_tokens", 0) for r in records)
    uncached_input = sum(
        max(r.get("input_tokens", 0) - r.get("cached_input_tokens", 0), 0) for r in records
    )
    return CacheStats(
        total_calls=total,
        cache_hits=hits,
        hit_ratio=(hits / total) if total else 0.0,
        cached_input_tokens=cached,
        uncached_input_tokens=uncached_input,
    )
