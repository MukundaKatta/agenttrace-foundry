"""Provider protocol and the in-process fake used by tests and demos.

The real Foundry adapter lives outside this package because we do not call
real LLMs in tests. See DEPLOY.md for the swap.

The fake provider is deterministic: same seed plus same task list plus same
config produces the same trace every time. That keeps the demo and the tests
honest.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any, Protocol

from .trace import CallEvent


class FoundryProvider(Protocol):
    """Minimal contract any Foundry adapter implements.

    `run_task` returns a list of CallEvent records that describe what the
    agent did, plus a `final_ok` flag and a `final_output` string. The
    harness never inspects the provider's internals.
    """

    def run_task(self, task_id: str, prompt: str) -> "ProviderResult": ...


@dataclass
class ProviderResult:
    """What a FoundryProvider returns for a single task run."""

    events: list[CallEvent]
    final_ok: bool
    final_output: str


@dataclass
class FakeFoundryProvider:
    """Deterministic stand-in for a real Foundry-hosted reasoning agent.

    Args:
        seed: RNG seed. Same seed plus same prompts produces the same trace.
        base_failure_rate: 0..1 probability a tool call fails with bad args.
        cache_warmup_after: cache hits start appearing after this many calls.
        slow_task_every: every Nth task gets injected p95-pumping latency.
        model: model id the provider claims to be running.
    """

    seed: int = 0
    base_failure_rate: float = 0.20
    cache_warmup_after: int = 3
    slow_task_every: int = 4
    model: str = "foundry-reasoning-mini"
    _calls: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def run_task(self, task_id: str, prompt: str) -> ProviderResult:
        """Simulate a multi-step reasoning agent answering a prompt."""

        # Per-task RNG so the trace stays stable when other tasks change.
        per_task_seed = int(
            hashlib.sha256(f"{self.seed}:{task_id}".encode()).hexdigest()[:8], 16
        )
        rng = random.Random(per_task_seed)
        events: list[CallEvent] = []

        # Step 1: plan. Always an LLM call.
        events.append(
            CallEvent(
                task_id=task_id,
                step=1,
                kind="llm",
                model=self.model,
                input_tokens=rng.randint(200, 400),
                output_tokens=rng.randint(80, 160),
                cached_input_tokens=0,
                latency_ms=rng.uniform(400, 700),
                ok=True,
                cache_hit=False,
            )
        )

        # Step 2: tool call. May fail with bad args; harness can retry.
        tool_ok = rng.random() > self.base_failure_rate
        retried = 0
        if not tool_ok:
            events.append(
                CallEvent(
                    task_id=task_id,
                    step=2,
                    kind="tool",
                    model=self.model,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=rng.uniform(40, 90),
                    ok=False,
                    error_code="missing_arg",
                    retried=1,
                )
            )
            retried = 1

        events.append(
            CallEvent(
                task_id=task_id,
                step=2 if tool_ok else 3,
                kind="tool",
                model=self.model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=rng.uniform(80, 160),
                ok=True,
                retried=retried,
            )
        )

        # Step 3: synthesize. Possible prompt-cache hit once warmed up.
        cache_warm = self._calls >= self.cache_warmup_after
        cached_input = rng.randint(120, 240) if cache_warm else 0
        is_slow = (self._calls + 1) % self.slow_task_every == 0
        synth_latency = rng.uniform(800, 1200) if not is_slow else rng.uniform(2400, 3200)
        events.append(
            CallEvent(
                task_id=task_id,
                step=3 if tool_ok else 4,
                kind="llm",
                model=self.model,
                input_tokens=rng.randint(300, 500),
                output_tokens=rng.randint(150, 300),
                cached_input_tokens=cached_input,
                latency_ms=synth_latency,
                ok=True,
                cache_hit=cache_warm,
            )
        )

        # Occasional silent failure: synth returns ok=True but final answer is
        # unusable. The judge function downstream catches it.
        final_ok = rng.random() > 0.10
        self._calls += 1
        return ProviderResult(
            events=events,
            final_ok=final_ok,
            final_output=f"brief-{task_id}-rev{1 + retried}",
        )


def default_judge(_prompt: str, _output: Any, ok: bool) -> bool:
    """Trivial pass-through judge.

    Real deployments replace this with a real evaluator. For the demo we trust
    the provider's `final_ok` flag.
    """

    return ok
