"""Programmatic signature structural self-check (workflow §5.1)."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from cpmpy_wfm_policy.pipeline.domain_inputs import (
    gated_tool_names,
    load_tools_json_file,
)
from cpmpy_wfm_policy.pipeline.signature_analysis import (
    _is_cp_var_ctor,
    build_helper_dependency_graph,
)


@dataclass
class SignatureFinding:
    code: str
    message: str
    detail: str | None = None

    def to_jsonable(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SignatureCheckReport:
    pass_: bool
    findings: list[SignatureFinding] = field(default_factory=list)

    def to_jsonable(self) -> dict[str, Any]:
        return {"pass": self.pass_, "findings": [f.to_jsonable() for f in self.findings]}

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_jsonable(), indent=2), encoding="utf-8")


_FORBIDDEN_TOPLEVEL = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Try,
    ast.With,
    ast.For,
    ast.While,
    ast.If,
    ast.Match,
)


def _flatten_tool_dep_symbols(entries: list[Any]) -> list[str]:
    names: list[str] = []
    for e in entries:
        if isinstance(e, str):
            names.append(e)
        elif isinstance(e, dict) and "name" in e:
            names.append(str(e["name"]))
    return names


def _enum_dict_valid(node: ast.Dict) -> tuple[bool, str | None]:
    codes: list[int] = []
    for k, v in zip(node.keys, node.values, strict=False):
        if k is None or v is None:
            return False, "enum dict has unpack"
        if not isinstance(k, ast.Constant) or not isinstance(k.value, str):
            return False, "enum keys must be string constants"
        if not isinstance(v, ast.Constant) or not isinstance(v.value, int):
            return False, "enum values must be int constants"
        codes.append(v.value)
    if len(codes) < 2:
        return False, "enum needs at least two values"
    sorted_codes = sorted(set(codes))
    if sorted_codes != list(range(len(sorted_codes))):
        return False, f"enum codes must be 0..n-1 contiguous, got {sorted_codes}"
    return True, None


def _import_allowlist_ok(nodes: list[ast.stmt]) -> list[SignatureFinding]:
    findings: list[SignatureFinding] = []
    for n in nodes:
        if isinstance(n, ast.Import):
            for alias in n.names:
                if alias.name != "cpmpy" or alias.asname not in (None, "cp"):
                    findings.append(
                        SignatureFinding(
                            code="import_not_allowed",
                            message="only `import cpmpy as cp` is allowed in section 1",
                            detail=alias.name,
                        )
                    )
        elif isinstance(n, ast.ImportFrom):
            if n.module != "cpmpy":
                findings.append(
                    SignatureFinding(
                        code="import_from_not_allowed",
                        message="ImportFrom only allowed from cpmpy",
                        detail=n.module,
                    )
                )
    return findings


def _cp_ctor_name_keyword(call: ast.Call) -> tuple[str | None, ast.AST | None]:
    """Return (name str or None, name value node)."""
    name_val = None
    for kw in call.keywords:
        if kw.arg == "name":
            return "present", kw.value
    return None, None


def _is_int_const(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, int)


def check_signature_structure(
    signature_py: str,
    *,
    tools_json_path: Path | None = None,
    require_tools_json_alignment: bool = True,
) -> SignatureCheckReport:
    findings: list[SignatureFinding] = []

    try:
        tree = ast.parse(signature_py)
    except SyntaxError as e:
        return SignatureCheckReport(
            False,
            [
                SignatureFinding(
                    code="syntax_error",
                    message="signature is not valid Python",
                    detail=str(e),
                )
            ],
        )

    if not tree.body:
        return SignatureCheckReport(
            False, [SignatureFinding(code="empty_module", message="signature module is empty")]
        )

    # No forbidden top-level statements
    for i, node in enumerate(tree.body):
        if isinstance(node, _FORBIDDEN_TOPLEVEL):
            findings.append(
                SignatureFinding(
                    code="forbidden_toplevel",
                    message=f"disallowed top-level {type(node).__name__}",
                    detail=f"statement index {i}",
                )
            )
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            # docstring-like is stored differently in py3.8+ - usually first Expr is docstring
            pass
        elif isinstance(node, ast.Expr):
            findings.append(
                SignatureFinding(
                    code="forbidden_toplevel",
                    message="top-level expressions are not allowed",
                    detail=f"statement index {i}",
                )
            )

    # Import block at start (allow only Import/ImportFrom first, then other stmts)
    first_non_import = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            first_non_import += 1
        else:
            break
    import_nodes = tree.body[:first_non_import]
    findings.extend(_import_allowlist_ok(import_nodes))

    assigns: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    assigns.append((t.id, node.value))

    names_assigned = [n for n, _ in assigns]
    if len(names_assigned) != len(set(names_assigned)):
        dup = [n for n in set(names_assigned) if names_assigned.count(n) > 1]
        findings.append(
            SignatureFinding(
                code="duplicate_assignment",
                message="same symbol assigned more than once",
                detail=", ".join(dup),
            )
        )

    tool_dep_node: ast.Dict | None = None
    domain_dim_node: ast.Dict | None = None
    test_bounds_node: ast.Dict | None = None
    tool_dep_literal: dict[Any, Any] | None = None
    has_vector_var = False

    for name, rhs in assigns:
        if name == "TOOL_DEPENDENCIES" and isinstance(rhs, ast.Dict):
            tool_dep_node = rhs
        if name == "DOMAIN_DIMENSIONS" and isinstance(rhs, ast.Dict):
            domain_dim_node = rhs
        if name == "TEST_SHAPE_BOUNDS" and isinstance(rhs, ast.Dict):
            test_bounds_node = rhs
        if _is_cp_var_ctor(rhs):
            for kw in rhs.keywords:  # type: ignore[arg-type]
                if kw.arg == "shape":
                    has_vector_var = True
                    break

    declared_for_deps: set[str] = set()
    for name, rhs in assigns:
        if name in ("TOOL_DEPENDENCIES", "DOMAIN_DIMENSIONS", "TEST_SHAPE_BOUNDS", "GLOBAL_CONSTRAINTS"):
            continue
        if name.isupper() and isinstance(rhs, ast.Dict):
            ok, err = _enum_dict_valid(rhs)
            if not ok:
                findings.append(
                    SignatureFinding(
                        code="invalid_enum_dict",
                        message=err or "invalid enum",
                        detail=name,
                    )
                )
            else:
                declared_for_deps.add(name)
            continue
        if _is_cp_var_ctor(rhs):
            call = rhs  # type: ignore[assignment]
            if not isinstance(call, ast.Call):
                continue
            if any(kw.arg == "shape" for kw in call.keywords):
                has_vector_var = True
            okn, name_node = _cp_ctor_name_keyword(call)
            if okn is None:
                findings.append(
                    SignatureFinding(
                        code="cp_var_missing_name",
                        message="cp intvar/boolvar must pass name=",
                        detail=name,
                    )
                )
            elif isinstance(name_node, ast.Constant) and name_node.value != name:
                findings.append(
                    SignatureFinding(
                        code="name_kw_mismatch",
                        message="name= must match Python variable name",
                        detail=f"{name} vs {getattr(name_node, 'value', None)}",
                    )
                )
            # bounds: intvar lower/upper must be int constants or boolvar has no bounds
            if isinstance(call.func, ast.Attribute) and call.func.attr == "intvar":
                if len(call.args) < 2:
                    findings.append(
                        SignatureFinding(
                            code="intvar_bounds",
                            message="cp.intvar needs explicit integer bounds",
                            detail=name,
                        )
                    )
                else:
                    if not _is_int_const(call.args[0]) or not _is_int_const(call.args[1]):
                        findings.append(
                            SignatureFinding(
                                code="intvar_bounds_non_literal",
                                message="bounds must be explicit integers (no expressions)",
                                detail=name,
                            )
                        )
            declared_for_deps.add(name)
            continue
        # helper or stray assign
        if isinstance(rhs, ast.Dict) and name.isupper():
            continue
        declared_for_deps.add(name)

    if has_vector_var:
        if domain_dim_node is None:
            findings.append(
                SignatureFinding(
                    code="missing_domain_dimensions",
                    message="DOMAIN_DIMENSIONS required when vector fields exist",
                    detail=None,
                )
            )
        if test_bounds_node is None:
            findings.append(
                SignatureFinding(
                    code="missing_test_shape_bounds",
                    message="TEST_SHAPE_BOUNDS required when vector fields exist",
                    detail=None,
                )
            )
        if domain_dim_node is not None:
            for k, v in zip(domain_dim_node.keys, domain_dim_node.values, strict=False):
                if not isinstance(k, ast.Constant) or not isinstance(k.value, str):
                    findings.append(
                        SignatureFinding(
                            code="domain_dim_key",
                            message="DOMAIN_DIMENSIONS keys must be string constants",
                        )
                    )
                    continue
                dim_name = k.value
                if not dim_name.isupper():
                    findings.append(
                        SignatureFinding(
                            code="domain_dim_name_case",
                            message="dimension names should be UPPER_SNAKE_CASE",
                            detail=dim_name,
                        )
                    )
                if not _is_int_const(v) or (isinstance(v, ast.Constant) and v.value <= 0):  # type: ignore[arg-type]
                    findings.append(
                        SignatureFinding(
                            code="domain_dim_value",
                            message="DOMAIN_DIMENSIONS values must be positive int constants",
                            detail=dim_name,
                        )
                    )

    if tool_dep_node is None:
        findings.append(
            SignatureFinding(code="missing_tool_dependencies", message="TOOL_DEPENDENCIES dict missing")
        )
    else:
        try:
            tool_dep_literal = ast.literal_eval(tool_dep_node)
        except Exception as e:
            findings.append(
                SignatureFinding(
                    code="tool_dependencies_not_literal",
                    message="TOOL_DEPENDENCIES must be a static dict literal",
                    detail=str(e),
                )
            )
            tool_dep_literal = None
        if isinstance(tool_dep_literal, dict):
            all_syms: set[str] = set()
            for tool_name, entries in tool_dep_literal.items():
                if not isinstance(entries, (list, tuple)):
                    findings.append(
                        SignatureFinding(
                            code="tool_dep_value_shape",
                            message="each TOOL_DEPENDENCIES value must be a list",
                            detail=str(tool_name),
                        )
                    )
                    continue
                for sym in _flatten_tool_dep_symbols(list(entries)):
                    all_syms.add(sym)
            unknown = sorted(all_syms - declared_for_deps)
            if unknown:
                findings.append(
                    SignatureFinding(
                        code="tool_dep_unknown_symbol",
                        message="TOOL_DEPENDENCIES references undeclared symbol",
                        detail=", ".join(unknown),
                    )
                )

    # Helper DAG
    try:
        g = build_helper_dependency_graph(signature_py)
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(n: str) -> None:
            if n in visiting:
                raise ValueError(n)
            if n in visited:
                return
            visiting.add(n)
            for m in g.get(n, ()):
                visit(m)
            visiting.discard(n)
            visited.add(n)

        for node in g:
            if node not in visited:
                visit(node)
    except ValueError as e:
        findings.append(
            SignatureFinding(
                code="helper_cycle",
                message="helper dependency cycle",
                detail=str(e),
            )
        )

    # Monotonic template order (soft): first stmt import; last assign TOOL_DEPENDENCIES
    if tree.body:
        last_meaningful = None
        for node in reversed(tree.body):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                last_meaningful = node
                continue
            last_meaningful = node
            break
        if isinstance(last_meaningful, ast.Assign):
            ids = [t.id for t in last_meaningful.targets if isinstance(t, ast.Name)]
            if ids and ids[0] != "TOOL_DEPENDENCIES":
                findings.append(
                    SignatureFinding(
                        code="tool_dependencies_not_last",
                        message="TOOL_DEPENDENCIES should be the final declaration block",
                        detail=f"last assign targets {ids}",
                    )
                )

    # tools.json alignment
    if tools_json_path and tools_json_path.is_file() and require_tools_json_alignment:
        try:
            tools = load_tools_json_file(tools_json_path)
            gated = set(gated_tool_names(tools))
            if isinstance(tool_dep_literal, dict):
                keys = set(tool_dep_literal.keys())
                if keys != gated:
                    findings.append(
                        SignatureFinding(
                            code="tools_json_tool_keys_mismatch",
                            message="TOOL_DEPENDENCIES keys must match gated tools.json names",
                            detail=f"deps={sorted(keys)} gated={sorted(gated)}",
                        )
                    )
        except Exception as e:
            findings.append(
                SignatureFinding(
                    code="tools_json_invalid",
                    message="failed to read/parse tools.json",
                    detail=str(e),
                )
            )

    pass_ = not findings
    return SignatureCheckReport(pass_=pass_, findings=findings)


def check_signature_file(
    signature_path: Path,
    *,
    tools_json_path: Path | None = None,
    require_tools_json_alignment: bool = True,
) -> SignatureCheckReport:
    text = Path(signature_path).read_text(encoding="utf-8")
    tpath = tools_json_path
    if tpath is None:
        candidate = Path(signature_path).resolve().parent / "tools.json"
        if candidate.is_file():
            tpath = candidate
    return check_signature_structure(
        text,
        tools_json_path=tpath,
        require_tools_json_alignment=require_tools_json_alignment,
    )
