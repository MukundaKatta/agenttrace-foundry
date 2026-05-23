"""FakeFoundryProvider tests."""

from agenttrace_foundry.provider import FakeFoundryProvider


def test_fake_provider_is_deterministic_for_same_seed() -> None:
    a = FakeFoundryProvider(seed=42)
    b = FakeFoundryProvider(seed=42)
    result_a = a.run_task("t1", "do thing")
    result_b = b.run_task("t1", "do thing")
    assert result_a.final_ok == result_b.final_ok
    assert result_a.final_output == result_b.final_output
    assert len(result_a.events) == len(result_b.events)
    for ea, eb in zip(result_a.events, result_b.events):
        assert ea.input_tokens == eb.input_tokens
        assert ea.output_tokens == eb.output_tokens
        assert ea.latency_ms == eb.latency_ms


def test_fake_provider_emits_plan_tool_synth_events() -> None:
    p = FakeFoundryProvider(seed=1)
    result = p.run_task("t1", "prompt")
    kinds = [e.kind for e in result.events]
    assert kinds.count("llm") >= 2
    assert kinds.count("tool") >= 1


def test_fake_provider_warms_up_cache_after_threshold() -> None:
    p = FakeFoundryProvider(seed=1, cache_warmup_after=2)
    seen_hit = False
    for idx in range(6):
        result = p.run_task(f"t{idx}", "prompt")
        for event in result.events:
            if event.cache_hit:
                seen_hit = True
    assert seen_hit, "expected at least one cache hit once warmup threshold passed"
