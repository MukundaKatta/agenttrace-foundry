"""Tool-arg vetting tests."""

from agenttrace_foundry.vet import ToolSpec, vet_args


SPECS = {
    "search": ToolSpec(
        name="search",
        required=("query", "limit"),
        types={"query": "str", "limit": "int"},
    ),
}


def test_vet_args_accepts_well_formed_call() -> None:
    result = vet_args("search", {"query": "AI", "limit": 5}, SPECS)
    assert result.ok is True
    assert result.hint is None


def test_vet_args_rejects_missing_arg_with_hint() -> None:
    result = vet_args("search", {"query": "AI"}, SPECS)
    assert result.ok is False
    assert result.error_code == "missing_arg"
    assert "limit" in (result.hint or "")


def test_vet_args_rejects_bad_type_with_hint() -> None:
    result = vet_args("search", {"query": "AI", "limit": "five"}, SPECS)
    assert result.ok is False
    assert result.error_code == "bad_type"
    assert "limit" in (result.hint or "")
    assert "int" in (result.hint or "")


def test_vet_args_rejects_bool_for_int_field() -> None:
    # bool is a subclass of int in Python; we treat that as a type error.
    result = vet_args("search", {"query": "AI", "limit": True}, SPECS)
    assert result.ok is False
    assert result.error_code == "bad_type"


def test_vet_args_unknown_tool_returns_unknown_tool_code() -> None:
    result = vet_args("teleport", {}, SPECS)
    assert result.ok is False
    assert result.error_code == "unknown_tool"
    assert "teleport" in (result.hint or "")
