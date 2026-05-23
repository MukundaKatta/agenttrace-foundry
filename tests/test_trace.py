"""Trace and percentile tests."""

import pytest

from agenttrace_foundry.trace import CallEvent, Trace, percentile


def test_percentile_handles_empty() -> None:
    assert percentile([], 50) == 0.0


def test_percentile_p50_p95() -> None:
    values = [100.0, 200.0, 300.0, 400.0, 500.0]
    assert percentile(values, 50) == pytest.approx(300.0)
    assert percentile(values, 95) == pytest.approx(480.0)


def test_percentile_clamps_out_of_range() -> None:
    values = [10.0, 20.0, 30.0]
    assert percentile(values, -5) == 10.0
    assert percentile(values, 150) == 30.0


def test_trace_aggregates_latency_retries_cache_hits() -> None:
    trace = Trace(task_id="t1")
    trace.add(
        CallEvent(task_id="t1", step=1, kind="llm", model="m", latency_ms=100.0)
    )
    trace.add(
        CallEvent(
            task_id="t1",
            step=2,
            kind="tool",
            model="m",
            latency_ms=50.0,
            retried=1,
        )
    )
    trace.add(
        CallEvent(
            task_id="t1",
            step=3,
            kind="llm",
            model="m",
            latency_ms=200.0,
            cache_hit=True,
        )
    )
    assert trace.total_latency_ms() == pytest.approx(350.0)
    assert trace.retries() == 1
    assert trace.cache_hits() == 1
