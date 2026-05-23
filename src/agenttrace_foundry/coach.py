"""AgentTraceCoach: the harness that wraps any FoundryProvider.

Run N tasks through the provider, record traces, compute a Leaderboard that
includes:
    - cost_per_success ($)
    - tool_arg_failure_rate (%)
    - p50 / p95 latency (ms)
    - drift_vs_baseline (cosine similarity)
    - retries triggered
    - cache hits

Each row maps to a shipped library of the user's:
    - cost_per_success      -> claude-cost / bedrock-cost shape (cost.py)
    - tool_arg_failure_rate -> agentvet (vet.py)
    - p50 / p95             -> agenttrace (trace.py)
    - drift_vs_baseline     -> driftvane (drift.py)
    - retries triggered     -> llm-retry pattern, surfaced from trace events
    - cache hits            -> cachebench (cache.py)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .cache import cache_stats
from .cost import DEFAULT_PRICES, ModelPrice, total_cost
from .drift import compute_drift
from .provider import FoundryProvider, default_judge
from .trace import CallEvent, Trace, percentile
from .vet import ToolArgResult, ToolSpec, vet_args


@dataclass
class RunRecord:
    """Single task run as exposed to coach consumers."""

    task_id: str
    trace: Trace
    final_output: str
    final_ok: bool
    tool_arg_errors: int


@dataclass
class Leaderboard:
    """Final aggregated metrics. Floats are rounded at format time, not here."""

    total_tasks: int
    successes: int
    failures: int
    total_cost_usd: float
    cost_per_success_usd: float
    tool_arg_failure_rate: float  # 0..1
    p50_latency_ms: float
    p95_latency_ms: float
    drift_mean_similarity: float
    drift_min_similarity: float
    drifted_tasks: tuple[str, ...]
    retries_triggered: int
    cache_hits: int
    cache_hit_ratio: float

    def as_dict(self) -> dict[str, float | int | tuple[str, ...]]:
        return {
            "total_tasks": self.total_tasks,
            "successes": self.successes,
            "failures": self.failures,
            "total_cost_usd": self.total_cost_usd,
            "cost_per_success_usd": self.cost_per_success_usd,
            "tool_arg_failure_rate": self.tool_arg_failure_rate,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "drift_mean_similarity": self.drift_mean_similarity,
            "drift_min_similarity": self.drift_min_similarity,
            "drifted_tasks": self.drifted_tasks,
            "retries_triggered": self.retries_triggered,
            "cache_hits": self.cache_hits,
            "cache_hit_ratio": self.cache_hit_ratio,
        }


@dataclass
class AgentTraceCoach:
    """Harness around a FoundryProvider.

    Args:
        provider: any object implementing FoundryProvider.
        tool_specs: optional registry for tool-arg vetting. Empty means skip.
        prices: per-model price table; defaults to cost.DEFAULT_PRICES.
        baseline_outputs: task_id -> reference text for drift checks.
        drift_threshold: cosine similarity below this counts as drifted.
        judge: optional callable to override provider.final_ok.
    """

    provider: FoundryProvider
    tool_specs: dict[str, ToolSpec] = field(default_factory=dict)
    prices: dict[str, ModelPrice] = field(default_factory=lambda: dict(DEFAULT_PRICES))
    baseline_outputs: dict[str, str] = field(default_factory=dict)
    drift_threshold: float = 0.95
    judge: Callable[[str, str, bool], bool] = default_judge

    def run(self, tasks: list[tuple[str, str]]) -> tuple[list[RunRecord], Leaderboard]:
        """Run all tasks and produce per-task records plus the leaderboard."""

        records: list[RunRecord] = []
        all_events: list[CallEvent] = []
        outputs: dict[str, str] = {}

        for task_id, prompt in tasks:
            result = self.provider.run_task(task_id, prompt)
            trace = Trace(task_id=task_id, events=list(result.events))
            tool_errors = self._vet_tool_events(trace.events)

            judged_ok = self.judge(prompt, result.final_output, result.final_ok)
            trace.finish(judged_ok)
            outputs[task_id] = result.final_output

            records.append(
                RunRecord(
                    task_id=task_id,
                    trace=trace,
                    final_output=result.final_output,
                    final_ok=judged_ok,
                    tool_arg_errors=tool_errors,
                )
            )
            all_events.extend(trace.events)

        leaderboard = self._build_leaderboard(records, all_events, outputs)
        return records, leaderboard

    # Internals.

    def _vet_tool_events(self, events: list[CallEvent]) -> int:
        """Re-vet tool calls against the registered specs.

        The fake provider already marks bad-arg tool calls. Real providers may
        not. This loop also lets a real harness count vet failures separately
        from provider-side ok=False events.
        """

        if not self.tool_specs:
            return sum(1 for e in events if e.kind == "tool" and not e.ok)
        count = 0
        for event in events:
            if event.kind != "tool":
                continue
            if not event.ok and event.error_code == "missing_arg":
                count += 1
                continue
            args = event.metadata.get("args", {})
            tool = event.metadata.get("tool")
            if tool is None:
                continue
            result: ToolArgResult = vet_args(tool, args, self.tool_specs)
            if not result.ok:
                count += 1
        return count

    def _build_leaderboard(
        self,
        records: list[RunRecord],
        events: list[CallEvent],
        outputs: dict[str, str],
    ) -> Leaderboard:
        total = len(records)
        successes = sum(1 for r in records if r.final_ok)
        failures = total - successes

        # Cost: only LLM events have token counts. cost.total_cost ignores
        # zero-token rows but we pass only LLM rows to keep intent obvious.
        llm_rows = [
            {
                "model": e.model,
                "input_tokens": e.input_tokens,
                "output_tokens": e.output_tokens,
                "cached_input_tokens": e.cached_input_tokens,
            }
            for e in events
            if e.kind == "llm"
        ]
        cost = total_cost(llm_rows, self.prices)

        tool_events = [e for e in events if e.kind == "tool"]
        tool_failure_rate = (
            (sum(1 for e in tool_events if not e.ok) / len(tool_events))
            if tool_events
            else 0.0
        )

        latencies = [e.latency_ms for e in events if e.latency_ms > 0]
        p50 = percentile(latencies, 50)
        p95 = percentile(latencies, 95)

        drift = compute_drift(outputs, self.baseline_outputs, self.drift_threshold)

        retries = sum(e.retried for e in events)
        cache_records = [
            {
                "cache_hit": e.cache_hit,
                "input_tokens": e.input_tokens,
                "cached_input_tokens": e.cached_input_tokens,
            }
            for e in events
            if e.kind == "llm"
        ]
        cs = cache_stats(cache_records)

        return Leaderboard(
            total_tasks=total,
            successes=successes,
            failures=failures,
            total_cost_usd=cost,
            cost_per_success_usd=(cost / successes) if successes else float("inf"),
            tool_arg_failure_rate=tool_failure_rate,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            drift_mean_similarity=drift.mean_similarity,
            drift_min_similarity=drift.min_similarity,
            drifted_tasks=drift.drifted_tasks,
            retries_triggered=retries,
            cache_hits=cs.cache_hits,
            cache_hit_ratio=cs.hit_ratio,
        )


def format_leaderboard(lb: Leaderboard) -> str:
    """Render the Leaderboard as a plain-text table for the demo."""

    cost_per_success = (
        f"${lb.cost_per_success_usd:.4f}" if lb.successes else "n/a"
    )
    rows = [
        ("total_tasks", str(lb.total_tasks)),
        ("successes", str(lb.successes)),
        ("failures", str(lb.failures)),
        ("total_cost_usd", f"${lb.total_cost_usd:.4f}"),
        ("cost_per_success_usd", cost_per_success),
        ("tool_arg_failure_rate", f"{lb.tool_arg_failure_rate * 100:.1f}%"),
        ("p50_latency_ms", f"{lb.p50_latency_ms:.0f} ms"),
        ("p95_latency_ms", f"{lb.p95_latency_ms:.0f} ms"),
        ("drift_mean_similarity", f"{lb.drift_mean_similarity:.3f}"),
        ("drift_min_similarity", f"{lb.drift_min_similarity:.3f}"),
        ("drifted_tasks", ",".join(lb.drifted_tasks) or "-"),
        ("retries_triggered", str(lb.retries_triggered)),
        ("cache_hits", str(lb.cache_hits)),
        ("cache_hit_ratio", f"{lb.cache_hit_ratio * 100:.1f}%"),
    ]
    width = max(len(name) for name, _ in rows)
    lines = ["Leaderboard", "-" * (width + 16)]
    for name, value in rows:
        lines.append(f"{name.ljust(width)}  {value}")
    return "\n".join(lines)
