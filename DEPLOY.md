# Deploying against a real Microsoft Foundry agent

The harness ships with `FakeFoundryProvider` so the demo and tests run with no API keys. Below is how you point it at a real Microsoft Foundry agent.

## Prerequisites

- Azure subscription with access to Microsoft Foundry (Azure AI Foundry).
- A Foundry project and an Agent created in that project. Note the project endpoint URL and the agent id.
- Local Azure credentials. `DefaultAzureCredential` from `azure-identity` works with `az login`, managed identity, or a service principal.

```bash
pip install azure-ai-projects azure-identity
az login
```

## Implement a FoundryProvider

Drop this file next to your script. It is the only piece of glue you need.

```python
# foundry_provider.py
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from agenttrace_foundry.provider import ProviderResult
from agenttrace_foundry.trace import CallEvent


class FoundryAdapter:
    def __init__(self, project_endpoint: str, agent_id: str):
        self._client = AIProjectClient(
            endpoint=project_endpoint,
            credential=DefaultAzureCredential(),
        )
        self._agent_id = agent_id

    def run_task(self, task_id: str, prompt: str) -> ProviderResult:
        thread = self._client.agents.threads.create()
        self._client.agents.messages.create(thread.id, role="user", content=prompt)
        run = self._client.agents.runs.create_and_process(
            thread_id=thread.id, agent_id=self._agent_id
        )

        # Map each agent step to a CallEvent. Field names below depend on the
        # Foundry SDK version; adjust to the shape your run object exposes.
        events: list[CallEvent] = []
        for idx, step in enumerate(run.steps, start=1):
            events.append(
                CallEvent(
                    task_id=task_id,
                    step=idx,
                    kind="llm" if step.kind == "model" else "tool",
                    model=getattr(step, "model", "foundry-reasoning-pro"),
                    input_tokens=getattr(step.usage, "input_tokens", 0),
                    output_tokens=getattr(step.usage, "output_tokens", 0),
                    cached_input_tokens=getattr(step.usage, "cached_input_tokens", 0),
                    latency_ms=getattr(step, "latency_ms", 0.0),
                    ok=step.status == "completed",
                    error_code=getattr(step, "error_code", None),
                )
            )

        return ProviderResult(
            events=events,
            final_ok=run.status == "completed",
            final_output=run.output_text or "",
        )
```

## Wire it into the coach

```python
from agenttrace_foundry import AgentTraceCoach
from foundry_provider import FoundryAdapter

provider = FoundryAdapter(
    project_endpoint="https://<your-project>.azurefoundry.com",
    agent_id="asst_...",
)
coach = AgentTraceCoach(provider=provider)
records, leaderboard = coach.run([
    ("t01", "Write a research brief on latent diffusion."),
    ("t02", "Write a research brief on retrieval-augmented agents."),
])
print(leaderboard)
```

## Pricing

`cost.py` ships a placeholder price table. Replace `DEFAULT_PRICES` with your real Foundry contract rates before reporting cost to anyone who cares.

```python
from agenttrace_foundry.cost import ModelPrice
prices = {
    "gpt-5.4": ModelPrice(input_per_million=2.50, output_per_million=10.00),
    "foundry-reasoning-pro": ModelPrice(input_per_million=3.00, output_per_million=15.00),
}
coach = AgentTraceCoach(provider=provider, prices=prices)
```

## Drift baseline

Record the agent's first known-good outputs and feed them back in as `baseline_outputs={task_id: text}`. The harness will flag any task whose new output drifts below `drift_threshold` (default 0.95).

## What you should not do

- Do not put live API keys in the repo. Use `DefaultAzureCredential` or env vars.
- Do not call real LLMs from the test suite. Tests are seed-deterministic on purpose.
