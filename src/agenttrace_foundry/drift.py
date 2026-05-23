"""Drift detection vs a recorded baseline.

We compute a deterministic, tokenizer-free embedding (32-dim character bag) for
each task's final output and compare cosine similarity against the same task's
baseline embedding. A run that drifts below the threshold is flagged.

The embedding is intentionally simple. The point is to demonstrate the seam
the user's driftvane library plugs into. Swap `_embed` for a real model in
production without changing the rest of the harness.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


_EMBED_DIM = 32


def _embed(text: str) -> list[float]:
    """Cheap deterministic embedding: bucketed character histogram."""

    vec = [0.0] * _EMBED_DIM
    for ch in text:
        vec[ord(ch) % _EMBED_DIM] += 1.0
    # L2 normalize. Empty input falls back to a unit vector so cosine is 0.
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""

    if len(a) != len(b):
        raise ValueError("Vector length mismatch")
    return sum(x * y for x, y in zip(a, b))


@dataclass(frozen=True)
class DriftResult:
    """Per-run drift score plus the same number averaged across tasks."""

    mean_similarity: float
    min_similarity: float
    drifted_tasks: tuple[str, ...]


def compute_drift(
    outputs: dict[str, str], baseline: dict[str, str], threshold: float = 0.95
) -> DriftResult:
    """Compare new outputs against a baseline map of task_id -> reference text.

    Tasks missing from the baseline are skipped. Returns mean and min cosine
    similarity across compared tasks, plus the set of tasks below `threshold`.
    """

    sims: list[float] = []
    drifted: list[str] = []
    for task_id, output in outputs.items():
        if task_id not in baseline:
            continue
        sim = cosine(_embed(output), _embed(baseline[task_id]))
        sims.append(sim)
        if sim < threshold:
            drifted.append(task_id)
    if not sims:
        return DriftResult(mean_similarity=0.0, min_similarity=0.0, drifted_tasks=())
    return DriftResult(
        mean_similarity=sum(sims) / len(sims),
        min_similarity=min(sims),
        drifted_tasks=tuple(drifted),
    )
