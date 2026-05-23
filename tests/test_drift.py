"""Drift detection tests."""

import pytest

from agenttrace_foundry.drift import compute_drift, cosine


def test_cosine_identical_vectors_is_one() -> None:
    a = [1.0, 0.0]
    assert cosine(a, a) == pytest.approx(1.0)


def test_cosine_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        cosine([1.0], [1.0, 0.0])


def test_compute_drift_identical_outputs_have_high_similarity() -> None:
    outputs = {"t1": "brief-t1-rev1", "t2": "brief-t2-rev1"}
    baseline = dict(outputs)
    result = compute_drift(outputs, baseline, threshold=0.99)
    assert result.mean_similarity == pytest.approx(1.0)
    assert result.drifted_tasks == ()


def test_compute_drift_flags_changed_outputs() -> None:
    outputs = {
        "t1": "brief-t1-rev1",
        "t2": "completely different output xyz!!! @@@",
    }
    baseline = {"t1": "brief-t1-rev1", "t2": "brief-t2-rev1"}
    result = compute_drift(outputs, baseline, threshold=0.95)
    assert "t2" in result.drifted_tasks
    assert "t1" not in result.drifted_tasks


def test_compute_drift_skips_unknown_tasks() -> None:
    result = compute_drift({"new": "x"}, {"old": "y"}, threshold=0.95)
    assert result.drifted_tasks == ()
    assert result.mean_similarity == 0.0
