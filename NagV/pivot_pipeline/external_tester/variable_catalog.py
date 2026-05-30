"""Variable sort harvest and catalog for external fill prompts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pivot_pipeline.external_tester.variable_tiers import Tier, tiers_for_meta
from pivot_pipeline.policy_literals import harvest_policy_literals
from pivot_pipeline.ir import MetaScheme
from pivot_pipeline.registry_pass import collect_used_slugs

_BOOL_OPS = frozenset({"EQ", "NEQ"})


def _walk_condition(obj: Any, *, bool_vars: set[str], int_vars: set[str]) -> None:
    if isinstance(obj, dict):
        k = obj.get("kind")
        if k == "atom":
            v = obj.get("variable")
            val = obj.get("value")
            if isinstance(v, str):
                if isinstance(val, bool):
                    bool_vars.add(v)
                elif isinstance(val, (int, float)):
                    int_vars.add(v)
        elif k in ("and", "or"):
            for c in obj.get("children") or []:
                _walk_condition(c, bool_vars=bool_vars, int_vars=int_vars)
        elif k == "not":
            _walk_condition(obj.get("child"), bool_vars=bool_vars, int_vars=int_vars)
        else:
            for vv in obj.values():
                _walk_condition(vv, bool_vars=bool_vars, int_vars=int_vars)
    elif isinstance(obj, list):
        for it in obj:
            _walk_condition(it, bool_vars=bool_vars, int_vars=int_vars)


def harvest_variable_sorts(rules: list[dict[str, Any]]) -> dict[str, Literal["int", "bool"]]:
    """Infer int/bool sorts from rule JSON (domain-agnostic)."""
    bool_vars: set[str] = set()
    int_vars: set[str] = set()
    slug_skip = re.compile(r"^[A-Z][A-Z0-9_]*$")

    for r in rules:
        if not isinstance(r, dict):
            continue
        tc = r.get("template_class")
        v = r.get("variable")
        if isinstance(v, str) and not slug_skip.match(v):
            cv = r.get("constant_value")
            if isinstance(cv, bool):
                bool_vars.add(v)
            elif isinstance(cv, (int, float)):
                int_vars.add(v)
            else:
                int_vars.add(v)
        for key in ("trigger_condition", "required_condition", "preempting_condition", "left", "right"):
            if key in r:
                _walk_condition(r[key], bool_vars=bool_vars, int_vars=int_vars)
        if tc == "K_OF_N":
            rv = r.get("result_variable")
            if isinstance(rv, str) and rv.strip():
                bool_vars.add(rv.strip())
        if isinstance(r.get("clauses"), list):
            for c in r["clauses"]:
                if isinstance(c, dict) and isinstance(c.get("variable"), str):
                    int_vars.add(c["variable"])
        if isinstance(r.get("terms"), list):
            for t in r["terms"]:
                if isinstance(t, dict) and isinstance(t.get("variable"), str):
                    int_vars.add(t["variable"])

    for name in collect_used_slugs(rules):
        if name in bool_vars:
            continue
        if name not in int_vars:
            int_vars.add(name)

    out: dict[str, Literal["int", "bool"]] = {}
    all_names = set(bool_vars) | set(int_vars)
    for n in sorted(all_names):
        out[n] = "bool" if n in bool_vars else "int"
    return out


def ensure_meta_variable_sorts(meta: MetaScheme, rules: list[dict[str, Any]]) -> MetaScheme:
    """Merge harvested sorts into meta (never drop K_OF_N result_variable etc.)."""
    harvested = harvest_variable_sorts(rules)
    if not harvested and not meta.variable_sorts:
        raise ValueError("could not harvest any variable sorts from rules")
    merged: dict[str, Literal["int", "bool"]] = dict(harvested)
    for name, sort in (meta.variable_sorts or {}).items():
        if name not in merged:
            merged[name] = sort  # type: ignore[assignment]
    return meta.model_copy(update={"variable_sorts": merged})


def write_variable_catalog(
    work_dir: Path,
    meta: MetaScheme,
    *,
    rules: list[dict[str, Any]] | None = None,
) -> Path:
    tiers: dict[str, Tier] = {}
    if rules is not None:
        tiers = tiers_for_meta(meta, rules)
    rows = [
        {
            "name": k,
            "sort": meta.variable_sorts[k],
            **({"tier": tiers[k]} if tiers else {}),
        }
        for k in sorted(meta.variable_sorts.keys())
    ]
    path = work_dir / "variable_catalog.json"
    payload: dict[str, Any] = {"variables": rows}
    if rules is not None:
        payload["policy_literal_values"] = harvest_policy_literals(rules)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def catalog_prompt_excerpt(meta: MetaScheme, *, max_chars: int = 12_000) -> str:
    lines = ["### Variable catalog (every key required in assignments)", ""]
    for name in sorted(meta.variable_sorts.keys()):
        lines.append(f"- `{name}` ({meta.variable_sorts[name]})")
    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[: max_chars - 40] + "\n... (truncated)\n"
    return text


__all__ = [
    "catalog_prompt_excerpt",
    "ensure_meta_variable_sorts",
    "harvest_variable_sorts",
    "write_variable_catalog",
]
