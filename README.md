# agenttrace-foundry

Reasoning Agent QA Coach for Microsoft Foundry.

Drop the harness around any multi-step Foundry agent run and you get a leaderboard with cost-per-success, tool-arg-failure rate, p50/p95 latency, drift-vs-baseline, retries, and cache hits. No code changes inside the agent.

Built for the Microsoft Agents League (AI Skills Fest), Reasoning Agents track.

## Quickstart

```bash
git clone https://github.com/MukundaKatta/agenttrace-foundry.git
cd agenttrace-foundry
python3 -m venv .venv && .venv/bin/pip install -e . pytest
.venv/bin/pytest -q
.venv/bin/python examples/leaderboard_demo.py
```

## What you get

A `FakeFoundryProvider` lets you see the whole flow without any API keys. Real Foundry deployment is a 10-line swap (see `DEPLOY.md`).

```python
from agenttrace_foundry import AgentTraceCoach, FakeFoundryProvider

tasks = [(f"t{i:02d}", f"Write a research brief on topic {i}.") for i in range(1, 11)]
baseline = {tid: f"brief-{tid}-rev1" for tid, _ in tasks}

coach = AgentTraceCoach(
    provider=FakeFoundryProvider(seed=3),
    baseline_outputs=baseline,
    drift_threshold=0.98,
)
records, leaderboard = coach.run(tasks)
print(leaderboard)
```

## Sample leaderboard

```
Scene 1: bare Foundry agent. No harness, no visibility.

  Tasks run:   10
  Successes:   9
  Failures:    1
  Cost:        unknown
  Drift:       unknown

Scene 2: same agent wrapped by AgentTraceCoach.

Leaderboard
-------------------------------------
total_tasks            10
successes              9
failures               1
total_cost_usd         $0.0105
cost_per_success_usd   $0.0012
tool_arg_failure_rate  23.1%
p50_latency_ms         607 ms
p95_latency_ms         1714 ms
drift_mean_similarity  0.988
drift_min_similarity   0.957
drifted_tasks          t01,t04,t05
retries_triggered      6
cache_hits             7
cache_hit_ratio        35.0%
```

## How each row gets computed

Every metric maps to a small, single-purpose library I shipped earlier. The harness is the seam that pulls them together for Foundry.

| Row                     | Module           | Inspired by                  |
| ----------------------- | ---------------- | ---------------------------- |
| `cost_per_success_usd`  | `cost.py`        | claude-cost, bedrock-cost    |
| `tool_arg_failure_rate` | `vet.py`         | agentvet                     |
| `p50_latency_ms`        | `trace.py`       | agenttrace                   |
| `p95_latency_ms`        | `trace.py`       | agenttrace                   |
| `drift_mean_similarity` | `drift.py`       | driftvane                    |
| `drift_min_similarity`  | `drift.py`       | driftvane                    |
| `retries_triggered`     | `coach.py`       | llm-retry, llm-circuit-breaker |
| `cache_hit_ratio`       | `cache.py`       | cachebench                   |

## Swap the fake for real Foundry

Implement `FoundryProvider`. The harness only needs `run_task(task_id, prompt)` to return events plus a final ok/output:

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from agenttrace_foundry import AgentTraceCoach
from agenttrace_foundry.provider import ProviderResult
from agenttrace_foundry.trace import CallEvent

class FoundryAdapter:
    def __init__(self, project, agent_id):
        self.client = AIProjectClient(endpoint=project, credential=DefaultAzureCredential())
        self.agent_id = agent_id

    def run_task(self, task_id, prompt):
        run = self.client.agents.runs.create_and_process(self.agent_id, prompt)
        events = [CallEvent(task_id=task_id, step=i, kind="llm", model=step.model,
                            input_tokens=step.input_tokens, output_tokens=step.output_tokens,
                            latency_ms=step.latency_ms, ok=step.ok)
                  for i, step in enumerate(run.steps, start=1)]
        return ProviderResult(events=events, final_ok=run.ok, final_output=run.output)

coach = AgentTraceCoach(provider=FoundryAdapter("https://...", "asst_..."))
```

See `DEPLOY.md` for the full Foundry path (Azure AI Foundry project, agent ids, env vars, telemetry mapping).

## Tests

```bash
.venv/bin/pytest -q
```

31 tests cover cost, vetting, tracing, drift, cache, provider determinism, and the end-to-end leaderboard.

## License

MIT. See `LICENSE`.
