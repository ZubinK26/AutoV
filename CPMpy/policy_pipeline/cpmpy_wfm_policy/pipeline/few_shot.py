"""Few-shot block for Formalizer user messages (Project_Spec_Agents)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _seed_path() -> Path:
    return Path(__file__).resolve().parents[1] / "llm" / "prompts" / "seed_examples.json"


def load_seed_example_dicts() -> list[dict[str, Any]]:
    p = _seed_path()
    if not p.is_file():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    return list(raw.get("examples", []))


def render_few_shot_examples_block(entries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, ex in enumerate(entries, start=1):
        lines.append(f"Example {i}:")
        lines.append(f"  NL: {ex.get('nl', '')}")
        lines.append(f"  Expression: {ex.get('expression', '')}")
        lines.append(f"  used_symbols: {ex.get('used_symbols', [])}")
        lines.append(f"  uses_global_constraints: {ex.get('uses_global_constraints', False)}")
        lines.append(f"  uses_vector_variables: {ex.get('uses_vector_variables', False)}")
        lines.append(f"  claimed_dependencies: {ex.get('claimed_dependencies', [])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def extract_expression_from_rule_module(rule_module: str) -> tuple[str, str]:
    """Return ``(rule_name, expression_src)`` from validated rule module text."""
    import ast

    tree = ast.parse(rule_module)
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and t.id.startswith("rule_"):
                return t.id, ast.unparse(node.value)
    raise ValueError("no rule_<k> = <expr> assignment found")


def recent_verified_examples(
    outputs: list[Any],
    nl_lines: list[str],
    max_n: int,
) -> list[dict[str, Any]]:
    if not outputs or max_n <= 0:
        return []
    start = max(0, len(outputs) - max_n)
    out: list[dict[str, Any]] = []
    for o, nl in zip(outputs[start:], nl_lines[start:], strict=True):
        try:
            _, expr = extract_expression_from_rule_module(o.rule_module)
        except (ValueError, SyntaxError):
            continue
        claimed = getattr(o, "claimed_dependencies", frozenset())
        if hasattr(claimed, "__iter__") and not isinstance(claimed, str):
            claimed_list = sorted(claimed)
        else:
            claimed_list = []
        out.append(
            {
                "nl": nl,
                "expression": expr,
                "used_symbols": sorted(o.used_symbols),
                "uses_global_constraints": o.uses_global_constraints,
                "uses_vector_variables": o.uses_vector_variables,
                "claimed_dependencies": claimed_list,
            }
        )
    return out


def compose_few_shot_block(
    *,
    rule_index: int,
    prior_outputs: list[Any],
    prior_nl_lines: list[str],
) -> str:
    seeds = load_seed_example_dicts()
    block_parts: list[dict[str, Any]] = []
    if rule_index <= 3:
        block_parts.extend(seeds)
    else:
        block_parts.extend(seeds)
        block_parts.extend(recent_verified_examples(prior_outputs, prior_nl_lines, 2))
    if not block_parts:
        return "(no few-shot examples; use signature and glossary only)\n"
    return render_few_shot_examples_block(block_parts)
