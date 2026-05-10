from __future__ import annotations

import json
import re
from typing import Any, Callable

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR

_SLUG_SKIP = re.compile(r"^R\d+$", re.IGNORECASE)


def normalize_slug_key(s: str) -> str:
    t = s.strip().lower().replace("-", "_")
    t = re.sub(r"\s+", "_", t)
    t = re.sub(r"[^a-z0-9_]+", "", t)
    return t.strip("_") or s.strip().lower()


def collect_used_slugs(rules: list[dict[str, Any]]) -> list[str]:
    found: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            k = obj.get("kind")
            if k == "atom":
                v = obj.get("variable")
                if isinstance(v, str) and not _SLUG_SKIP.match(v):
                    found.add(v)
            elif k == "varcmp":
                for key in ("left_variable", "right_variable"):
                    v = obj.get(key)
                    if isinstance(v, str) and not _SLUG_SKIP.match(v):
                        found.add(v)
            elif k == "varprod_cmp":
                for key in ("left_variable", "right_variable"):
                    v = obj.get(key)
                    if isinstance(v, str) and not _SLUG_SKIP.match(v):
                        found.add(v)
                rhs = obj.get("rhs")
                if isinstance(rhs, dict) and rhs.get("kind") == "var":
                    rv = rhs.get("variable")
                    if isinstance(rv, str) and not _SLUG_SKIP.match(rv):
                        found.add(rv)
            elif k in ("and", "or"):
                for c in obj.get("children") or []:
                    walk(c)
            elif k == "not":
                walk(obj.get("child"))
            else:
                for vk, vv in obj.items():
                    if vk in (
                        "trigger_condition",
                        "required_condition",
                        "preempting_condition",
                        "left",
                        "right",
                    ):
                        walk(vv)
                    elif vk in (
                        "variable",
                        "left_variable",
                        "right_variable",
                        "operand_1",
                        "operand_2",
                        "target_limit",
                    ):
                        if isinstance(vv, str) and not _SLUG_SKIP.match(vv):
                            found.add(vv)
                    elif vk == "variables" and isinstance(vv, list):
                        for item in vv:
                            if isinstance(item, str) and not _SLUG_SKIP.match(item):
                                found.add(item)
                    else:
                        walk(vv)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)

    for r in rules:
        walk(r)
    return sorted(found)


def build_alias_map(registry: dict[str, Any]) -> dict[str, str]:
    """normalized_key -> canonical id"""
    m: dict[str, str] = {}
    entries = registry.get("canonical_variables")
    if not isinstance(entries, list):
        return m
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        cid = ent.get("id")
        if not isinstance(cid, str) or not cid.strip():
            continue
        canon = cid.strip()
        keys = [canon, *([a for a in ent.get("aliases", []) if isinstance(a, str)])]
        for k in keys:
            nk = normalize_slug_key(k)
            if nk and nk not in m:
                m[nk] = canon
    return m


def _remap_var_name(name: str, alias_map: dict[str, str]) -> str:
    if _SLUG_SKIP.match(name):
        return name
    nk = normalize_slug_key(name)
    return alias_map.get(nk, name)


def apply_registry_to_rules(rules: list[dict[str, Any]], alias_map: dict[str, str]) -> list[dict[str, Any]]:
    if not alias_map:
        return [json.loads(json.dumps(r)) for r in rules]

    def walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            k = obj.get("kind")
            out = dict(obj)
            if k == "atom":
                v = out.get("variable")
                if isinstance(v, str):
                    out["variable"] = _remap_var_name(v, alias_map)
                return out
            if k == "varcmp":
                for key in ("left_variable", "right_variable"):
                    v = out.get(key)
                    if isinstance(v, str):
                        out[key] = _remap_var_name(v, alias_map)
                return out
            if k == "varprod_cmp":
                for key in ("left_variable", "right_variable"):
                    v = out.get(key)
                    if isinstance(v, str):
                        out[key] = _remap_var_name(v, alias_map)
                rhs = out.get("rhs")
                if isinstance(rhs, dict) and rhs.get("kind") == "var":
                    rhs = dict(rhs)
                    rv = rhs.get("variable")
                    if isinstance(rv, str):
                        rhs["variable"] = _remap_var_name(rv, alias_map)
                    out["rhs"] = rhs
                return out
            if k in ("and", "or"):
                ch = out.get("children")
                if isinstance(ch, list):
                    out["children"] = [walk(c) for c in ch]
                return out
            if k == "not":
                out["child"] = walk(out.get("child"))
                return out
            # Rule dict or other
            if "template_class" in out:
                for key in (
                    "variable",
                    "left_variable",
                    "right_variable",
                    "operand_1",
                ):
                    v = out.get(key)
                    if isinstance(v, str):
                        out[key] = _remap_var_name(v, alias_map)
                for key in ("operand_2", "target_limit"):
                    v = out.get(key)
                    if isinstance(v, str):
                        out[key] = _remap_var_name(v, alias_map)
                if isinstance(out.get("variables"), list):
                    out["variables"] = [
                        _remap_var_name(x, alias_map) if isinstance(x, str) else x for x in out["variables"]
                    ]
                for cond_key in (
                    "trigger_condition",
                    "required_condition",
                    "preempting_condition",
                    "left",
                    "right",
                ):
                    if cond_key in out:
                        out[cond_key] = walk(out[cond_key])
                return out
            return {kk: walk(vv) for kk, vv in out.items()}
        if isinstance(obj, list):
            return [walk(x) for x in obj]
        return obj

    return [walk(r) for r in rules]  # type: ignore[list-item]


def _registry_prompt_template() -> str:
    path = PROMPTS_DIR / "registry.md"
    if not path.is_file():
        raise FileNotFoundError(f"missing registry prompt: {path}")
    return path.read_text(encoding="utf-8")


def run_registry_pass(
    numbered_lines: list[tuple[int, str]],
    rules: list[dict[str, Any]],
    *,
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    slugs = collect_used_slugs(rules)
    lines_txt = "\n".join(f"{i}. {t}" for i, t in numbered_lines)
    slugs_txt = json.dumps(slugs, ensure_ascii=False)
    tmpl = _registry_prompt_template()
    prompt = tmpl.replace("<<<NUMBERED_LINES>>>", lines_txt).replace("<<<USED_SLUGS>>>", slugs_txt)
    raw = llm(prompt)
    reg = parse_json_object(raw)
    alias_map = build_alias_map(reg)
    updated = apply_registry_to_rules(rules, alias_map)
    return reg, updated


def registry_pass_from_nl_and_rules(
    nl_lines: list[str],
    rules: list[dict[str, Any]],
    *,
    llm: Callable[..., str] = pivot_llm_complete,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    numbered = [(i + 1, ln) for i, ln in enumerate(nl_lines)]
    return run_registry_pass(numbered, rules, llm=llm)
