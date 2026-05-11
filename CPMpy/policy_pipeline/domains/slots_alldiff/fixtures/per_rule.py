"""Per-rule fixtures for slots_alldiff (solver-backed cheap checks)."""

from __future__ import annotations


def base_state() -> dict[str, int | bool]:
    return {"slot_a": 0, "slot_b": 1, "slot_c": 2}


PER_RULE_FIXTURES: dict[str, list[tuple[dict[str, int | bool], bool]]] = {
    "rule_1": [
        (base_state(), True),
        ({"slot_a": 0, "slot_b": 0, "slot_c": 1}, False),
    ],
}
