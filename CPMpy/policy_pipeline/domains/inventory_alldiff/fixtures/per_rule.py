"""Per-rule fixtures: Pattern B + global AllDifferent."""

from __future__ import annotations

PER_RULE_FIXTURES: dict[str, list[tuple[dict[str, int | bool], bool]]] = {
    "rule_1": [
        (
            {"bin_counts[0]": 0, "bin_counts[1]": 1, "bin_counts[2]": 2},
            True,
        ),
        (
            {"bin_counts[0]": 5, "bin_counts[1]": 1, "bin_counts[2]": 2},
            False,
        ),
    ],
}
