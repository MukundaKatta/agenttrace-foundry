"""AgentTraceFoundry - governance and cost analysis harness for Microsoft Foundry reasoning agents.

Drop the harness around any multi-step agent run and you get a leaderboard with
cost-per-success, tool-arg-failure rate, p50/p95 latency, drift-vs-baseline,
retries triggered, and cache hits.

Public surface:
    - AgentTraceCoach: the harness itself
    - FakeFoundryProvider: deterministic provider for tests and demos
    - FoundryProvider: protocol any real Foundry adapter implements
    - Leaderboard, RunRecord: result types
"""

from .coach import AgentTraceCoach, Leaderboard, RunRecord
from .provider import FakeFoundryProvider, FoundryProvider

__all__ = [
    "AgentTraceCoach",
    "FakeFoundryProvider",
    "FoundryProvider",
    "Leaderboard",
    "RunRecord",
]

__version__ = "0.1.0"
