"""
Signature-level analysis: helper dependency DAG (Project_Spec §4 / template §6 CONFLICT).
"""

from __future__ import annotations

import ast
from pathlib import Path

from cpmpy_wfm_policy.pipeline.ast_validator import ASTValidationError

_RESERVED_TOPLEVEL = frozenset(
    {
        "cp",
        "cpmpy",
        "TOOL_DEPENDENCIES",
        "DOMAIN_DIMENSIONS",
        "TEST_SHAPE_BOUNDS",
        "GLOBAL_CONSTRAINTS",
    }
)


def _is_cp_var_ctor(rhs: ast.AST) -> bool:
    if not isinstance(rhs, ast.Call) or not isinstance(rhs.func, ast.Attribute):
        return False
    if not isinstance(rhs.func.value, ast.Name) or rhs.func.value.id != "cp":
        return False
    return rhs.func.attr in {"intvar", "boolvar", "cpm_array"}


def _target_names_comp(t: ast.AST) -> set[str]:
    if isinstance(t, ast.Name):
        return {t.id}
    if isinstance(t, (ast.Tuple, ast.List)):
        return set().union(*(_target_names_comp(x) for x in t.elts))
    raise ASTValidationError(f"unsupported comprehension target {ast.dump(t)}")


def _comprehension_bound_names(rhs: ast.AST) -> set[str]:
    b: set[str] = set()
    for n in ast.walk(rhs):
        if isinstance(n, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            for gen in n.generators:
                b |= _target_names_comp(gen.target)
        elif isinstance(n, ast.DictComp):
            for gen in n.generators:
                b |= _target_names_comp(gen.target)
    return b


def _rhs_ref_names(rhs: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(rhs) if isinstance(n, ast.Name)}


def _iter_module_assigns(tree: ast.Module) -> list[tuple[str, ast.AST]]:
    rows: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if isinstance(t, ast.Name):
                rows.append((t.id, node.value))
    return rows


def build_helper_dependency_graph(signature_py: str) -> dict[str, set[str]]:
    """Static deps among assigned names (excluding cp var constructors)."""
    tree = ast.parse(signature_py)
    assigns = _iter_module_assigns(tree)
    skip = _RESERVED_TOPLEVEL | frozenset({"range"})
    declared = frozenset(name for name, _ in assigns)
    deps: dict[str, set[str]] = {}
    for name, rhs in assigns:
        if name in _RESERVED_TOPLEVEL:
            continue
        if name.isupper() and isinstance(rhs, ast.Dict):
            continue
        if _is_cp_var_ctor(rhs):
            continue
        used = _rhs_ref_names(rhs) - _comprehension_bound_names(rhs) - skip - {name}
        deps[name] = set(used) & declared
    return deps


def validate_signature_helper_dag(signature_path: str | Path) -> None:
    """Raise ``ASTValidationError`` if the static helper graph has a cycle."""
    p = Path(signature_path)
    g = build_helper_dependency_graph(p.read_text(encoding="utf-8"))
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(n: str) -> None:
        if n in visiting:
            raise ASTValidationError(f"helper dependency cycle involving {n!r}")
        if n in visited:
            return
        visiting.add(n)
        for m in g.get(n, ()):
            visit(m)
        visiting.remove(n)
        visited.add(n)

    for node in g:
        if node not in visited:
            visit(node)
