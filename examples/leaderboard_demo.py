"""End-to-end demo: research-brief agent across 10 tasks.

Scene 1: bare provider. Just count successes and total wall time.
Scene 2: same provider wrapped by AgentTraceCoach. Print the full leaderboard.

Run:
    python examples/leaderboard_demo.py
"""

from __future__ import annotations

import time

from agenttrace_foundry import AgentTraceCoach, FakeFoundryProvider
from agenttrace_foundry.coach import format_leaderboard


TASKS = [
    (f"t{idx:02d}", f"Write a research brief on topic {idx}.")
    for idx in range(1, 11)
]

# Baseline outputs the agent produced last week. Used for drift checking.
BASELINE = {
    task_id: f"brief-{task_id}-rev1"
    for task_id, _ in TASKS
}


DEMO_SEED = 3


def scene_one() -> None:
    print("Scene 1: bare Foundry agent. No harness, no visibility.\n")
    provider = FakeFoundryProvider(seed=DEMO_SEED)
    successes = 0
    failures = 0
    start = time.perf_counter()
    for task_id, prompt in TASKS:
        result = provider.run_task(task_id, prompt)
        if result.final_ok:
            successes += 1
        else:
            failures += 1
    elapsed = (time.perf_counter() - start) * 1000.0
    print(f"  Tasks run:   {len(TASKS)}")
    print(f"  Successes:   {successes}")
    print(f"  Failures:    {failures}")
    print(f"  Wall time:   {elapsed:.0f} ms")
    print("  Cost:        unknown")
    print("  Drift:       unknown")
    print()


def scene_two() -> None:
    print("Scene 2: same agent wrapped by AgentTraceCoach.\n")
    provider = FakeFoundryProvider(seed=DEMO_SEED)
    coach = AgentTraceCoach(
        provider=provider,
        baseline_outputs=BASELINE,
        drift_threshold=0.98,
    )
    _records, leaderboard = coach.run(TASKS)
    print(format_leaderboard(leaderboard))
    print()


def main() -> None:
    scene_one()
    scene_two()


if __name__ == "__main__":
    main()
