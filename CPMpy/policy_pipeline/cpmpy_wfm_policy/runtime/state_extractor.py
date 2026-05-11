"""Tool dependency → state subset (Project_Spec §7.3)."""

from __future__ import annotations

from typing import Any


class StateExtractError(ValueError):
    """Missing snapshot data for extraction."""


def extract_tool_state(
    full_state: dict[str, Any],
    *,
    tool_dependencies: list[Any],
    call_params: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the state fragment required to evaluate rules for one tool call.

    - String entries: copy scalar ``full_state[name]``.
    - ``slice: "full"`` on a vector: expand ``full_state[name]`` list to ``name[i]`` keys
      if the snapshot uses flat CPMpy names; if already flat, copy matching ``name[*]`` keys.
    - ``by_index``: ``name[call_params[index_param]]``.
    - ``by_range``: ``name[i]`` for ``i`` in ``range(call_params[lower_param], call_params[upper_param]+1)``.
    """
    out: dict[str, Any] = {}
    for entry in tool_dependencies:
        if isinstance(entry, str):
            if entry not in full_state:
                raise StateExtractError(f"missing scalar field {entry!r}")
            out[entry] = full_state[entry]
            continue
        if not isinstance(entry, dict):
            raise StateExtractError(f"invalid dependency entry {entry!r}")
        name = entry["name"]
        mode = entry["slice"]
        if mode == "full":
            if name in full_state and isinstance(full_state[name], list):
                for i, val in enumerate(full_state[name]):
                    out[f"{name}[{i}]"] = val
                continue
            prefix = f"{name}["
            found = False
            for k, v in full_state.items():
                if isinstance(k, str) and k.startswith(prefix):
                    out[k] = v
                    found = True
            if not found:
                raise StateExtractError(f"missing vector field {name!r} (list or flat keys)")
            continue
        if mode == "by_index":
            idx_key = entry["index_param"]
            if idx_key not in call_params:
                raise StateExtractError(f"missing call param {idx_key!r}")
            idx = int(call_params[idx_key])
            flat = f"{name}[{idx}]"
            if flat in full_state:
                out[flat] = full_state[flat]
                continue
            if name in full_state and isinstance(full_state[name], list):
                out[flat] = full_state[name][idx]
                continue
            raise StateExtractError(f"missing index {flat!r} for vector {name!r}")
        if mode == "by_range":
            lo_p = entry["lower_param"]
            hi_p = entry["upper_param"]
            if lo_p not in call_params or hi_p not in call_params:
                raise StateExtractError("by_range requires lower_param and upper_param in call_params")
            lo = int(call_params[lo_p])
            hi = int(call_params[hi_p])
            for i in range(lo, hi + 1):
                flat = f"{name}[{i}]"
                if flat in full_state:
                    out[flat] = full_state[flat]
                elif name in full_state and isinstance(full_state[name], list):
                    out[flat] = full_state[name][i]
                else:
                    raise StateExtractError(f"missing {flat!r}")
            continue
        raise StateExtractError(f"unknown slice mode {mode!r}")
    return out
