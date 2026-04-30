from __future__ import annotations

import json
from importlib import resources
from typing import Any, TypedDict


class WriteStep(TypedDict, total=False):
    op: str
    tool: str
    args: dict[str, Any]


def load_scenarios_bundle() -> list[dict[str, Any]]:
    raw = resources.files("agentsim.runtime.data").joinpath("scenarios.json").read_text(encoding="utf-8")
    return json.loads(raw)


def run_write_steps(ctx: Any, steps: list[dict[str, Any]]) -> None:
    """Execute ``{"op":"write", "tool":..., "args":{}}`` steps in order."""

    wt = ctx.write_tools
    for s in steps:
        if s.get("op") != "write":
            continue
        getattr(wt, s["tool"])(**dict(s.get("args", {})))
