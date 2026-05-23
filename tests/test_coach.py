"""AgentTraceCoach end-to-end tests."""

import pytest

from agenttrace_foundry import AgentTraceCoach, FakeFoundryProvider
from agenttrace_foundry.coach import format_leaderboard


def _tasks(n: int) -> list[tuple[str, str]]:
    return [(f"t{i:02d}", f"prompt {i}") for i in range(1, n + 1)]


def test_coach_runs_all_tasks_and_returns_records() -> None:
    coach = AgentTraceCoach(provider=FakeFoundryProvider(seed=7))
    records, lb = coach.run(_tasks(10))
    assert len(records) == 10
    assert lb.total_tasks == 10
    assert lb.successes + lb.failures == 10


def test_coach_leaderboard_is_deterministic_for_same_seed() -> None:
    a = AgentTraceCoach(provider=FakeFoundryProvider(seed=7))
    b = AgentTraceCoach(provider=FakeFoundryProvider(seed=7))
    _, lb_a = a.run(_tasks(10))
    _, lb_b = b.run(_tasks(10))
    assert lb_a.as_dict() == lb_b.as_dict()


def test_coach_records_cost_per_success_when_any_success() -> None:
    coach = AgentTraceCoach(provider=FakeFoundryProvider(seed=7))
    _, lb = coach.run(_tasks(10))
    assert lb.total_cost_usd > 0
    if lb.successes > 0:
        assert lb.cost_per_success_usd == pytest.approx(
            lb.total_cost_usd / lb.successes
        )


def test_coach_records_p95_at_least_p50() -> None:
    coach = AgentTraceCoach(provider=FakeFoundryProvider(seed=7))
    _, lb = coach.run(_tasks(10))
    assert lb.p95_latency_ms >= lb.p50_latency_ms


def test_coach_counts_retries_when_provider_marks_them() -> None:
    # High base_failure_rate guarantees at least one retry inside 10 tasks.
    coach = AgentTraceCoach(
        provider=FakeFoundryProvider(seed=11, base_failure_rate=0.95)
    )
    _, lb = coach.run(_tasks(10))
    assert lb.retries_triggered >= 1


def test_coach_drift_against_baseline_is_perfect_when_outputs_match() -> None:
    provider = FakeFoundryProvider(seed=7)
    # First pass collects "baseline" outputs.
    baseline_records, _ = AgentTraceCoach(provider=provider).run(_tasks(5))
    baseline = {r.task_id: r.final_output for r in baseline_records}

    # Re-run with the same seed and check drift comes out at 1.0.
    coach = AgentTraceCoach(
        provider=FakeFoundryProvider(seed=7),
        baseline_outputs=baseline,
        drift_threshold=0.99,
    )
    _, lb = coach.run(_tasks(5))
    assert lb.drift_mean_similarity == pytest.approx(1.0)
    assert lb.drifted_tasks == ()


def test_coach_cache_hits_grow_over_time() -> None:
    coach = AgentTraceCoach(
        provider=FakeFoundryProvider(seed=7, cache_warmup_after=2)
    )
    _, lb = coach.run(_tasks(10))
    assert lb.cache_hits >= 1
    assert 0.0 < lb.cache_hit_ratio <= 1.0


def test_coach_format_leaderboard_renders_all_rows() -> None:
    coach = AgentTraceCoach(provider=FakeFoundryProvider(seed=7))
    _, lb = coach.run(_tasks(10))
    rendered = format_leaderboard(lb)
    for label in (
        "total_tasks",
        "successes",
        "failures",
        "cost_per_success_usd",
        "tool_arg_failure_rate",
        "p50_latency_ms",
        "p95_latency_ms",
        "drift_mean_similarity",
        "retries_triggered",
        "cache_hits",
    ):
        assert label in rendered
