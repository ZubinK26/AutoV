from __future__ import annotations

from agentsim.runtime.models import Decision, ToolCall


def always_allow_validate(_call: ToolCall, _state: dict) -> Decision:
    """Stub validator (Slice B): every write is permitted."""

    return Decision(allow=True)


def never_allow_validate(_call: ToolCall, _state: dict) -> Decision:
    """Test helper: blocks with a fixed explanation."""

    return Decision(allow=False, unsat_core=["RULE-STUB"], explanation="blocked by stub")
