"""
Validation of formalizer-emitted rule source (scalar + slice 5 comprehensions / subscripts).

See CPMpy/Project_Spec/01_project_specification.md §4.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, FrozenSet

_RULE_NAME_RE = re.compile(r"^rule_\d+$")

_BANNED_NODE_TYPES: frozenset[type[ast.AST]] = frozenset(
    {
        ast.For,
        ast.While,
        ast.If,
        ast.IfExp,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.Lambda,
        ast.ClassDef,
        ast.Try,
        ast.With,
        ast.Yield,
        ast.YieldFrom,
        ast.Return,
        ast.Global,
        ast.Nonlocal,
        ast.AugAssign,
        ast.AnnAssign,
        ast.Delete,
        ast.Raise,
        ast.Assert,
        ast.NamedExpr,
        ast.Match,
    }
)

# Section-2-style enumeration dicts: string keys here are Python source keys, not CPMpy string values.
_ENUM_DICT_SUBSCRIPT_NAMES: frozenset[str] = frozenset(
    {"KYC_STATUS", "REFUND_TYPE", "TRANSACTION_STATUS"}
)


_ALLOWED_CP_CALL_NAMES: FrozenSet[str] = frozenset(
    {
        "intvar",
        "boolvar",
        "cpm_array",
        "any",
        "all",
        "sum",
        "min",
        "max",
        "abs",
        "AllDifferent",
        "AllDifferentExcept0",
        "AllEqual",
        "Circuit",
        "Cumulative",
        "Element",
        "GlobalCardinalityCount",
        "IfThenElse",
        "InDomain",
        "Inverse",
        "Regular",
        "Table",
        "NegativeTable",
        "ShortTable",
        "Xor",
        "Increasing",
        "Decreasing",
        "LexLess",
        "LexLessEq",
    }
)

_ALLOWED_BINOPS: frozenset[type[ast.operator]] = frozenset(
    {
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.FloorDiv,
        ast.Mod,
        ast.BitAnd,
        ast.BitOr,
        ast.BitXor,
    }
)
_ALLOWED_CMPS: frozenset[type[ast.cmpop]] = frozenset(
    {
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
    }
)
_ALLOWED_BOOLOPS: frozenset[type[ast.boolop]] = frozenset({ast.And, ast.Or})
_ALLOWED_UNARYOPS: frozenset[type[ast.unaryop]] = frozenset(
    {ast.Not, ast.Invert, ast.USub, ast.UAdd}
)


class ASTValidationError(ValueError):
    """Rule source failed AST allowlist checks."""


@dataclass(frozen=True)
class RuleMetadata:
    used_symbols: frozenset[str] | None = None
    uses_global_constraints: bool | None = None
    uses_vector_variables: bool | None = None


def load_signature_namespace(path: str) -> dict[str, Any]:
    import importlib.util

    spec = importlib.util.spec_from_file_location("domain_signature", path)
    if spec is None or spec.loader is None:
        raise ASTValidationError(f"cannot load signature from {path!r}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(vars(mod))


def signature_allowed_names(namespace: dict[str, Any]) -> frozenset[str]:
    return frozenset(
        k
        for k in namespace
        if not k.startswith("_") and k not in {"cp", "cpmpy"}
    )


def global_constraints_from_namespace(ns: dict[str, Any]) -> list[Any]:
    raw = ns.get("GLOBAL_CONSTRAINTS")
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return [raw]


def dimension_constant_names(namespace: dict[str, Any]) -> frozenset[str]:
    """``DOMAIN_DIMENSIONS`` / ``TEST_SHAPE_BOUNDS`` keys as strings."""
    names: set[str] = set()
    dd = namespace.get("DOMAIN_DIMENSIONS")
    if isinstance(dd, dict):
        names |= {str(k) for k in dd}
    tb = namespace.get("TEST_SHAPE_BOUNDS")
    if isinstance(tb, dict):
        names |= {str(k) for k in tb}
    return frozenset(names)


def vector_decl_names(namespace: dict[str, Any]) -> frozenset[str]:
    """Names bound to CPMpy variables with a non-empty ``shape``."""
    skip = frozenset(
        {
            "TOOL_DEPENDENCIES",
            "DOMAIN_DIMENSIONS",
            "TEST_SHAPE_BOUNDS",
            "GLOBAL_CONSTRAINTS",
        }
    )
    out: set[str] = set()
    for k, v in namespace.items():
        if k.startswith("_") or k in skip or k in {"cp", "cpmpy"}:
            continue
        sh = getattr(v, "shape", None)
        if sh is not None and sh != ():
            out.add(k)
    return frozenset(out)


def default_allowed_imports() -> frozenset[tuple[str, str]]:
    return frozenset({("cpmpy", "cp")})


def _extract_import_map(
    tree: ast.Module, allowed: frozenset[tuple[str, str]]
) -> dict[str, str]:
    imap: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for al in node.names:
                mod_root = al.name.split(".")[0]
                alias = al.asname or al.name
                if (mod_root, alias) not in allowed:
                    raise ASTValidationError(
                        f"import not allowed: {al.name!r} as {alias!r}; allowlist={sorted(allowed)}"
                    )
                imap[alias] = mod_root
        elif isinstance(node, ast.ImportFrom):
            raise ASTValidationError("from-imports are not allowed in rule modules")
        else:
            break
    if not imap:
        raise ASTValidationError("rule module must contain at least one allowed import")
    return imap


_RULE_BUILTIN_NAMES = frozenset({"range"})


def validate_rule_ast(
    source: str,
    *,
    signature_namespace: dict[str, Any],
    allowed_imports: frozenset[tuple[str, str]] | None = None,
    metadata: RuleMetadata | None = None,
) -> tuple[str, ast.Module]:
    allowed_imports = allowed_imports or default_allowed_imports()
    allowed_names = signature_allowed_names(signature_namespace)
    dim_names = dimension_constant_names(signature_namespace)
    vnames = vector_decl_names(signature_namespace)

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ASTValidationError(f"syntax error: {e}") from e

    if not isinstance(tree, ast.Module):
        raise ASTValidationError("expected a module body")

    import_map = _extract_import_map(tree, allowed_imports)

    rest = [
        n
        for n in tree.body
        if not isinstance(n, ast.Import | ast.ImportFrom)
    ]
    if len(rest) != 1 or not isinstance(rest[0], ast.Assign):
        raise ASTValidationError("expected exactly one top-level assignment after imports (the rule)")

    assign = rest[0]
    if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
        raise ASTValidationError("rule assignment target must be a single name")
    rule_name = assign.targets[0].id
    if not _RULE_NAME_RE.match(rule_name):
        raise ASTValidationError(f"rule name must match rule_<n>, got {rule_name!r}")

    _walk_expr(assign.value, import_map, allowed_names, dim_names, frozenset())

    bound = _comprehension_bindings(assign.value)
    referenced = _collect_referenced_names(assign.value) - bound
    ref_for_symbols = referenced - frozenset(import_map.keys()) - _RULE_BUILTIN_NAMES

    unknown = ref_for_symbols - allowed_names
    if unknown:
        raise ASTValidationError(f"references disallowed or undefined names: {sorted(unknown)}")

    if metadata and metadata.used_symbols is not None:
        if ref_for_symbols != metadata.used_symbols:
            raise ASTValidationError(
                f"used_symbols mismatch: AST has {sorted(ref_for_symbols)}, "
                f"metadata has {sorted(metadata.used_symbols)}"
            )
    if metadata and metadata.uses_global_constraints is not None:
        flags = _detect_uses_global(assign.value)
        if flags != metadata.uses_global_constraints:
            raise ASTValidationError(
                f"uses_global_constraints mismatch: AST {flags}, metadata {metadata.uses_global_constraints}"
            )
    if metadata and metadata.uses_vector_variables is not None:
        vec = _detect_uses_vector(assign.value, vnames)
        if vec != metadata.uses_vector_variables:
            raise ASTValidationError(
                f"uses_vector_variables mismatch: AST {vec}, metadata {metadata.uses_vector_variables}"
            )

    return rule_name, tree


def _comp_target_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return set().union(*(_comp_target_names(x) for x in target.elts))
    raise ASTValidationError(f"unsupported comprehension target {ast.dump(target, include_attributes=False)}")


def _comprehension_bindings(node: ast.AST) -> set[str]:
    b: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            for gen in child.generators:
                b |= _comp_target_names(gen.target)
        elif isinstance(child, ast.DictComp):
            for gen in child.generators:
                b |= _comp_target_names(gen.target)
    return b


def _validate_comp_iter(
    node: ast.AST,
    import_map: dict[str, str],
    allowed_names: frozenset[str],
    dim_names: frozenset[str],
    local_names: frozenset[str],
) -> None:
    if isinstance(node, ast.Name):
        if node.id not in allowed_names and node.id not in local_names:
            raise ASTValidationError(
                f"comprehension iterable {node.id!r} must be a signature collection or outer local"
            )
        return
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
        if len(node.args) < 1 or len(node.args) > 3:
            raise ASTValidationError("range() in comprehension must have 1..3 arguments")
        for arg in node.args:
            if isinstance(arg, ast.Constant):
                if not isinstance(arg.value, int):
                    raise ASTValidationError("range() bounds must be integers")
            elif isinstance(arg, ast.Name):
                if (
                    arg.id not in dim_names
                    and arg.id not in allowed_names
                    and arg.id not in local_names
                ):
                    raise ASTValidationError(
                        f"range() bound {arg.id!r} must be a dimension or signature name"
                    )
            else:
                raise ASTValidationError("range() in comprehensions: only int literals or allowed names")
        return
    raise ASTValidationError(
        "disallowed comprehension iterable "
        f"(use a signature vector/collection or range(...)): {ast.dump(node, include_attributes=False)}"
    )


def _walk_comp_generators(
    generators: list[ast.comprehension],
    import_map: dict[str, str],
    allowed_names: frozenset[str],
    dim_names: frozenset[str],
    outer_locals: frozenset[str],
) -> frozenset[str]:
    loc = outer_locals
    for gen in generators:
        _validate_comp_iter(gen.iter, import_map, allowed_names, dim_names, loc)
        new = frozenset(_comp_target_names(gen.target))
        for ife in gen.ifs:
            _walk_expr(ife, import_map, allowed_names, dim_names, loc | new)
        loc = loc | new
    return loc


def _walk_expr(
    node: ast.AST,
    import_map: dict[str, str],
    allowed_names: frozenset[str],
    dim_names: frozenset[str],
    local_names: frozenset[str],
) -> None:
    if type(node) in _BANNED_NODE_TYPES:
        raise ASTValidationError(f"disallowed syntax: {type(node).__name__}")

    if isinstance(node, ast.Name):
        return

    if isinstance(node, ast.Constant):
        if not isinstance(node.value, bool | int | float | type(None)) and node.value is not ...:
            if isinstance(node.value, str):
                raise ASTValidationError("string literals are not allowed in rule expressions")
        return

    if isinstance(node, ast.ListComp):
        loc = _walk_comp_generators(
            node.generators, import_map, allowed_names, dim_names, local_names
        )
        _walk_expr(node.elt, import_map, allowed_names, dim_names, loc)
        return
    if isinstance(node, ast.SetComp):
        loc = _walk_comp_generators(
            node.generators, import_map, allowed_names, dim_names, local_names
        )
        _walk_expr(node.elt, import_map, allowed_names, dim_names, loc)
        return
    if isinstance(node, ast.GeneratorExp):
        loc = _walk_comp_generators(
            node.generators, import_map, allowed_names, dim_names, local_names
        )
        _walk_expr(node.elt, import_map, allowed_names, dim_names, loc)
        return
    if isinstance(node, ast.DictComp):
        loc = _walk_comp_generators(
            node.generators, import_map, allowed_names, dim_names, local_names
        )
        _walk_expr(node.key, import_map, allowed_names, dim_names, loc)
        _walk_expr(node.value, import_map, allowed_names, dim_names, loc)
        return

    if isinstance(node, ast.Attribute):
        _walk_expr(node.value, import_map, allowed_names, dim_names, local_names)
        return

    if isinstance(node, ast.Subscript):
        _walk_expr(node.value, import_map, allowed_names, dim_names, local_names)
        sl = node.slice
        if isinstance(sl, ast.Slice):
            for part in (sl.lower, sl.upper, sl.step):
                if part is not None:
                    _walk_expr(part, import_map, allowed_names, dim_names, local_names)
            return
        if isinstance(sl, ast.Tuple):
            for elt in sl.elts:
                _walk_expr(elt, import_map, allowed_names, dim_names, local_names)
            return
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
            if isinstance(node.value, ast.Name) and node.value.id in _ENUM_DICT_SUBSCRIPT_NAMES:
                return
            raise ASTValidationError(
                "string subscripts are only allowed on enumeration dicts "
                f"({', '.join(sorted(_ENUM_DICT_SUBSCRIPT_NAMES))})"
            )
        _walk_expr(sl, import_map, allowed_names, dim_names, local_names)
        return

    if isinstance(node, ast.Tuple | ast.List):
        for elt in node.elts:
            _walk_expr(elt, import_map, allowed_names, dim_names, local_names)
        return

    if isinstance(node, ast.BinOp):
        if type(node.op) not in _ALLOWED_BINOPS:
            raise ASTValidationError(f"disallowed binary op {type(node.op).__name__}")
        _walk_expr(node.left, import_map, allowed_names, dim_names, local_names)
        _walk_expr(node.right, import_map, allowed_names, dim_names, local_names)
        return

    if isinstance(node, ast.BoolOp):
        if type(node.op) not in _ALLOWED_BOOLOPS:
            raise ASTValidationError(f"disallowed bool op {type(node.op).__name__}")
        for v in node.values:
            _walk_expr(v, import_map, allowed_names, dim_names, local_names)
        return

    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _ALLOWED_UNARYOPS:
            raise ASTValidationError(f"disallowed unary op {type(node.op).__name__}")
        _walk_expr(node.operand, import_map, allowed_names, dim_names, local_names)
        return

    if isinstance(node, ast.Compare):
        _walk_expr(node.left, import_map, allowed_names, dim_names, local_names)
        for op in node.ops:
            if type(op) not in _ALLOWED_CMPS:
                raise ASTValidationError(f"disallowed comparator {type(op).__name__}")
        for comp in node.comparators:
            _walk_expr(comp, import_map, allowed_names, dim_names, local_names)
        return

    if isinstance(node, ast.Call):
        _validate_call(node, import_map, allowed_names, dim_names, local_names)
        return

    raise ASTValidationError(f"disallowed expression form: {type(node).__name__}")


def _validate_call(
    node: ast.Call,
    import_map: dict[str, str],
    allowed_names: frozenset[str],
    dim_names: frozenset[str],
    local_names: frozenset[str],
) -> None:
    func = node.func
    if isinstance(func, ast.Name) and func.id == "range":
        if len(node.args) < 1 or len(node.args) > 3:
            raise ASTValidationError("range() must have 1..3 arguments")
        for arg in node.args:
            if isinstance(arg, ast.Constant):
                if not isinstance(arg.value, int):
                    raise ASTValidationError("range() arguments must be integers")
            elif isinstance(arg, ast.Name):
                if (
                    arg.id not in dim_names
                    and arg.id not in allowed_names
                    and arg.id not in local_names
                ):
                    raise ASTValidationError(f"range() bound {arg.id!r} is not allowed here")
            else:
                raise ASTValidationError("unsupported range() argument form")
        return

    if isinstance(func, ast.Attribute) and func.attr == "implies":
        _walk_expr(func.value, import_map, allowed_names, dim_names, local_names)
        for arg in node.args:
            _walk_expr(arg, import_map, allowed_names, dim_names, local_names)
        for kw in node.keywords:
            _walk_expr(kw.value, import_map, allowed_names, dim_names, local_names)
        return

    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        base = func.value.id
        if base in import_map and import_map[base] == "cpmpy":
            if func.attr not in _ALLOWED_CP_CALL_NAMES:
                raise ASTValidationError(f"disallowed cp.{func.attr} call")
            for arg in node.args:
                _walk_expr(arg, import_map, allowed_names, dim_names, local_names)
            for kw in node.keywords:
                _walk_expr(kw.value, import_map, allowed_names, dim_names, local_names)
            return

    raise ASTValidationError(f"disallowed call shape: {ast.dump(func, include_attributes=False)}")


def _collect_referenced_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
    return names


def _detect_uses_global(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if isinstance(child.func.value, ast.Name) and child.func.value.id == "cp":
                if child.func.attr in _ALLOWED_CP_CALL_NAMES - {
                    "intvar",
                    "boolvar",
                    "cpm_array",
                    "any",
                    "all",
                    "sum",
                    "min",
                    "max",
                    "abs",
                }:
                    return True
    return False


def _detect_uses_vector(node: ast.AST, vector_names: frozenset[str]) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if child.func.attr in {"cpm_array"}:
                return True
            if isinstance(child.func.value, ast.Name) and child.func.value.id == "cp":
                if child.func.attr == "intvar" and any(
                    kw.arg == "shape" for kw in child.keywords if kw.arg is not None
                ):
                    return True
                if child.func.attr == "boolvar" and any(
                    kw.arg == "shape" for kw in child.keywords if kw.arg is not None
                ):
                    return True
        if isinstance(child, ast.Subscript):
            if isinstance(child.value, ast.Name) and child.value.id in vector_names:
                return True
    return False
