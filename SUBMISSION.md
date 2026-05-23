# agenttrace-foundry: Microsoft Agents League submission

Track: Reasoning Agents (Microsoft Foundry)
Author: Mukunda Katta
Repo: https://github.com/MukundaKatta/agenttrace-foundry

## The problem

You can stand up a Foundry reasoning agent in an afternoon. What you cannot do in an afternoon is answer the questions a real owner has after the first ten production runs.

- Are my agents actually succeeding or do they just look done?
- How much does one successful answer cost me?
- Which tools are failing because the model passes bad args, and how often?
- Is the new prompt drifting the agent's outputs away from what users expected last week?
- Are we silently paying retry tax?
- Is prompt caching helping at all?

Today these answers come from grepping logs, copying numbers into a spreadsheet, and squinting. They live in five different tools. None of them know what "success" means for your task.

agenttrace-foundry is a single QA harness that wraps any Foundry agent and produces one leaderboard with all of those numbers.

## The approach

A judge can drop one object around any `FoundryProvider`:

```python
coach = AgentTraceCoach(
    provider=my_foundry_adapter,
    baseline_outputs={"t01": "...", "t02": "..."},
)
records, leaderboard = coach.run(tasks)
```

The harness records every LLM call and tool call inside the run as a `CallEvent`. After all tasks finish, it computes seven rolled-up numbers:

- `cost_per_success_usd`
- `tool_arg_failure_rate`
- `p50_latency_ms`, `p95_latency_ms`
- `drift_mean_similarity`, `drift_min_similarity`, `drifted_tasks`
- `retries_triggered`
- `cache_hit_ratio`

Each metric is computed by a small, single-purpose module that mirrors the shape of a library I have already shipped to crates.io or PyPI under MukundaKatta. That part matters: the harness is not made of magic, it is a thin Foundry-shaped glue layer over building blocks that already work. Names below are the libraries on the public package indexes that the modules in this repo were modeled on.

| Leaderboard row         | This repo module | Sibling lib I shipped earlier |
| ----------------------- | ---------------- | ----------------------------- |
| `cost_per_success_usd`  | `cost.py`        | claude-cost, bedrock-cost      |
| `tool_arg_failure_rate` | `vet.py`         | agentvet, agentvet-rs          |
| `p50_latency_ms`        | `trace.py`       | agenttrace, agenttrace-rs      |
| `p95_latency_ms`        | `trace.py`       | agenttrace, agenttrace-rs      |
| `drift_mean_similarity` | `drift.py`       | driftvane                      |
| `drift_min_similarity`  | `drift.py`       | driftvane                      |
| `retries_triggered`     | `coach.py`       | llm-retry, llm-circuit-breaker |
| `cache_hit_ratio`       | `cache.py`       | cachebench                     |

## Demo

The repo ships `examples/leaderboard_demo.py`. It runs the same fake reasoning agent in two scenes.

Scene 1, no harness:

```
Tasks run:   10
Successes:   9
Failures:    1
Cost:        unknown
Drift:       unknown
```

Scene 2, same agent wrapped by AgentTraceCoach:

```
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

The fake provider is seed-deterministic. Same seed plus same task list always produces this exact leaderboard. That is also what lets the test suite have 31 green tests with no live LLM calls.

## Why this matters for Foundry specifically

Foundry already gives you a multi-step reasoning agent with tools and a thread/run model. What it does not give you out of the box is a sharp, judge-ready answer to "is this run any good and is it worth the spend." This harness answers that in one screen.

The `FoundryProvider` Protocol is two methods. A real adapter is roughly 20 lines on top of `azure-ai-projects` (full code in `DEPLOY.md`). The same harness then keeps working as you swap models, change prompts, add tools, or wire prompt caching: the leaderboard moves and you can see exactly which lever moved which row.

## Deploy story

`DEPLOY.md` walks the full path from `az login` to a working leaderboard against a real Foundry agent:

1. `pip install azure-ai-projects azure-identity` and `az login`.
2. Implement `FoundryAdapter.run_task` (about 20 lines, mapping each step in the Foundry run object to a `CallEvent`).
3. Pass real per-model rates to `AgentTraceCoach(prices=...)`.
4. Feed in a baseline outputs map for drift detection.
5. Run the harness. The leaderboard format is identical.

## What is in the repo

- `src/agenttrace_foundry/`: 7 small modules, total around 900 LOC including comments.
- `tests/`: 31 passing tests across cost, vet, trace, drift, cache, provider, and end-to-end coach behavior.
- `examples/leaderboard_demo.py`: the two-scene demo.
- `README.md`: quickstart and metric-to-module table.
- `DEPLOY.md`: the swap from fake to real Foundry.
- `DEMO_SCRIPT.md`: 90-second video script in three shots.

## What I am asking the judges to look at

1. Run `pytest -q`. Thirty-one tests, under a tenth of a second, no API keys.
2. Run `examples/leaderboard_demo.py`. See the two scenes side by side.
3. Read `DEPLOY.md`. Confirm the swap from fake to real Foundry is small and explicit.

If that lands, the harness is doing exactly what the pitch promised: it is a thin, useful, opinionated QA layer around Foundry reasoning agents that I can extend per-customer without breaking the public seam.
