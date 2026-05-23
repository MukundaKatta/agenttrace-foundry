# 90-second demo script

Three shots. No voice tricks. Plain narration in the speaker's own voice.

## Shot 1 (0:00 - 0:25): The problem

Terminal on screen. Run the bare Foundry agent across 10 tasks:

```bash
.venv/bin/python -c "
from agenttrace_foundry import FakeFoundryProvider
p = FakeFoundryProvider(seed=3)
ok = sum(1 for i in range(1,11) if p.run_task(f't{i:02d}','q').final_ok)
print(f'tasks: 10  successes: {ok}  cost: unknown  drift: unknown')
"
```

Narration:

> Here is a Microsoft Foundry reasoning agent running ten research-brief tasks. It tells me how many succeeded. It does not tell me what they cost, whether the outputs drifted from last week, or how often tools got called with bad args.

## Shot 2 (0:25 - 1:05): The harness

Same terminal, run the demo:

```bash
.venv/bin/python examples/leaderboard_demo.py
```

Pause on Scene 2's leaderboard. Highlight rows in order:

> Wrap the same agent in AgentTraceCoach. Same ten tasks, same seed. Now I see cost per success at one tenth of a cent. I see that tools got bad args 23 percent of the time and the harness retried six times. I see p95 latency at 1.7 seconds, where p50 was 600 milliseconds. Three tasks drifted below my 0.98 threshold. Cache hit ratio is 35 percent.

## Shot 3 (1:05 - 1:30): How it ships

Show the table in README.md mapping each row to a small module, then `DEPLOY.md` in the editor.

Narration:

> Every row is computed by a small module modeled on a library I already shipped: claude-cost, agentvet, agenttrace, driftvane, llm-retry, cachebench. The harness is the seam that pulls them together for Foundry. Swapping the fake provider for real Foundry is about twenty lines of `azure-ai-projects` calls. Full code is in DEPLOY.md. Repo is MukundaKatta slash agenttrace-foundry. Thanks.

## Recording checklist

- Terminal font at least 18pt so the leaderboard rows read on mobile.
- Run `clear` between Shot 1 and Shot 2 so the leaderboard lands on a clean screen.
- Mention the track name "Reasoning Agents" once near the end.
- No captions on the speaker's face; let the terminal carry the story.
