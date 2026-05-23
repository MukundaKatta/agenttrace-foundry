"""Trace recorder for agent runs.

Each agent run produces a list of CallEvent records. A Trace groups events
under a single task id and exposes latency aggregates (p50, p95) along with
success/failure counts.

This is the same shape the user's agenttrace crate exposes for Rust.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CallEvent:
    """A single LLM or tool call inside a run."""

    task_id: str
    step: int
    kind: str  # "llm" or "tool"
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    latency_ms: float = 0.0
    ok: bool = True
    error_code: str | None = None
    retried: int = 0
    cache_hit: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    """Trace for a single task. Holds every CallEvent emitted by the agent."""

    task_id: str
    events: list[CallEvent] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    final_ok: bool = False

    def add(self, event: CallEvent) -> None:
        self.events.append(event)

    def finish(self, ok: bool) -> None:
        self.finished_at = time.time()
        self.final_ok = ok

    def total_latency_ms(self) -> float:
        return sum(e.latency_ms for e in self.events)

    def retries(self) -> int:
        return sum(e.retried for e in self.events)

    def cache_hits(self) -> int:
        return sum(1 for e in self.events if e.cache_hit)


def percentile(values: list[float], pct: float) -> float:
    """Compute the linear-interpolation percentile of a list of floats.

    `pct` is 0..100. Empty input returns 0.0.
    """

    if not values:
        return 0.0
    if pct <= 0:
        return min(values)
    if pct >= 100:
        return max(values)
    ordered = sorted(values)
    # Standard nearest-rank with linear interpolation.
    rank = (pct / 100.0) * (len(ordered) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    frac = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac
