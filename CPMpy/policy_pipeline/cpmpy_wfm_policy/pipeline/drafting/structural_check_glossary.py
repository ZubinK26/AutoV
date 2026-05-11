"""Programmatic glossary structural self-check (workflow §6.5)."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from cpmpy_wfm_policy.pipeline.signature_analysis import _is_cp_var_ctor

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


@dataclass
class GlossaryFinding:
    code: str
    message: str
    detail: str | None = None

    def to_jsonable(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class GlossaryCheckReport:
    pass_: bool
    findings: list[GlossaryFinding] = field(default_factory=list)

    def to_jsonable(self) -> dict[str, Any]:
        return {"pass": self.pass_, "findings": [f.to_jsonable() for f in self.findings]}

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_jsonable(), indent=2), encoding="utf-8")


def required_glossary_symbols_from_signature(signature_py: str) -> list[str]:
    """Symbols from template sections 2–6 (enums, fields, tool params, helpers)."""
    tree = ast.parse(signature_py)
    assigns: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    assigns.append((t.id, node.value))
    out: list[str] = []
    skip = frozenset({"TOOL_DEPENDENCIES", "DOMAIN_DIMENSIONS", "TEST_SHAPE_BOUNDS", "GLOBAL_CONSTRAINTS"})
    for name, rhs in assigns:
        if name in skip:
            continue
        if name.isupper() and isinstance(rhs, ast.Dict):
            out.append(name)
            continue
        if _is_cp_var_ctor(rhs):
            out.append(name)
            continue
        out.append(name)
    return sorted(frozenset(out))


def _entry_type_ok(t: str) -> bool:
    return t in ("enum", "scalar_field", "vector_field", "tool_parameter", "helper")


def check_glossary_structure(
    glossary_text: str,
    *,
    required_symbols: list[str],
    rules_text: str | None = None,
    domain_notes: str | None = None,
    inferred_phrase_symbols: frozenset[str] | None = None,
) -> GlossaryCheckReport:
    findings: list[GlossaryFinding] = []
    if yaml is None:
        return GlossaryCheckReport(
            False,
            [
                GlossaryFinding(
                    code="pyyaml_missing",
                    message="install PyYAML to validate glossary (pip install pyyaml)",
                )
            ],
        )
    try:
        data = yaml.safe_load(glossary_text)
    except Exception as e:
        return GlossaryCheckReport(
            False,
            [GlossaryFinding(code="yaml_parse_error", message="glossary is not valid YAML", detail=str(e))],
        )
    if not isinstance(data, dict):
        return GlossaryCheckReport(
            False,
            [GlossaryFinding(code="glossary_not_mapping", message="top-level YAML must be a mapping")],
        )

    blob_cf = ""
    if rules_text is not None or domain_notes is not None:
        blob_cf = f"{rules_text or ''}\n{domain_notes or ''}".casefold()

    inferred = inferred_phrase_symbols or frozenset()

    req = set(required_symbols)
    keys = set(str(k) for k in data.keys())
    missing = sorted(req - keys)
    if missing:
        findings.append(
            GlossaryFinding(
                code="glossary_missing_symbol",
                message="missing glossary entry for signature symbol",
                detail=", ".join(missing),
            )
        )
    orphans = sorted(keys - req)
    if orphans:
        findings.append(
            GlossaryFinding(
                code="glossary_orphan_entry",
                message="glossary entry not in signature sections 2–6",
                detail=", ".join(orphans),
            )
        )

    for sym in sorted(req & keys):
        entry = data.get(sym)
        if not isinstance(entry, dict):
            findings.append(
                GlossaryFinding(
                    code="glossary_entry_shape",
                    message="each entry must be a mapping",
                    detail=sym,
                )
            )
            continue
        desc = entry.get("description", "")
        if not isinstance(desc, str) or len(desc.strip()) < 20:
            findings.append(
                GlossaryFinding(
                    code="glossary_description_short",
                    message="description must be non-empty and at least 20 characters",
                    detail=sym,
                )
            )
        t = entry.get("type", "")
        if not isinstance(t, str) or not _entry_type_ok(t):
            findings.append(
                GlossaryFinding(
                    code="glossary_bad_type",
                    message="type must be one of enum|scalar_field|vector_field|tool_parameter|helper",
                    detail=sym,
                )
            )
        phrases = entry.get("example_nl_phrases")
        if not isinstance(phrases, list) or len(phrases) < 2:
            findings.append(
                GlossaryFinding(
                    code="glossary_phrases",
                    message="example_nl_phrases must be a list of at least 2 strings",
                    detail=sym,
                )
            )
        else:
            for i, ph in enumerate(phrases):
                if not isinstance(ph, str):
                    findings.append(
                        GlossaryFinding(
                            code="glossary_phrase_type",
                            message="example_nl_phrases items must be strings",
                            detail=f"{sym}[{i}]",
                        )
                    )
                    continue
                wc = len(ph.split())
                if wc < 4:
                    findings.append(
                        GlossaryFinding(
                            code="glossary_phrase_short",
                            message="each example_nl_phrases item should be at least 4 words",
                            detail=f"{sym}[{i}]",
                        )
                    )
                if blob_cf and sym not in inferred:
                    pcf = " ".join(ph.split()).casefold()
                    if pcf not in blob_cf and len(pcf) >= 12:
                        ok_chunk = False
                        step = max(12, min(32, len(pcf) // 2))
                        for j in range(0, max(1, len(pcf) - step + 1), max(1, step // 2)):
                            chunk = pcf[j : j + step]
                            if chunk in blob_cf:
                                ok_chunk = True
                                break
                        if not ok_chunk:
                            findings.append(
                                GlossaryFinding(
                                    code="glossary_phrase_not_in_rules",
                                    message="example_nl_phrases must be grounded in rules/domain_notes (substring) unless symbol is in entries_with_inferred_phrases",
                                    detail=f"{sym}[{i}]: {ph[:80]!r}",
                                )
                            )
        if t == "enum":
            vm = entry.get("value_meanings")
            if not isinstance(vm, dict) or not vm:
                findings.append(
                    GlossaryFinding(
                        code="glossary_enum_values",
                        message="enum entries require value_meanings map",
                        detail=sym,
                    )
                )
        if t == "helper":
            df = entry.get("derives_from")
            if not isinstance(df, list) or len(df) < 1:
                findings.append(
                    GlossaryFinding(
                        code="glossary_helper_derives",
                        message="helper entries require derives_from list of at least one symbol",
                        detail=sym,
                    )
                )
            elif not all(isinstance(x, str) for x in df):
                findings.append(
                    GlossaryFinding(
                        code="glossary_helper_derives_type",
                        message="derives_from must be strings",
                        detail=sym,
                    )
                )
            else:
                bad = [x for x in df if x not in req]
                if bad:
                    findings.append(
                        GlossaryFinding(
                            code="glossary_helper_unknown_dep",
                            message="derives_from references symbol not in signature glossary scope",
                            detail=f"{sym} -> {bad}",
                        )
                    )

    return GlossaryCheckReport(pass_=not findings, findings=findings)


def check_glossary_file(
    glossary_path: Path,
    *,
    signature_path: Path,
    rules_text: str | None = None,
    domain_notes: str | None = None,
    inferred_phrase_symbols: frozenset[str] | None = None,
) -> GlossaryCheckReport:
    sig = Path(signature_path).read_text(encoding="utf-8")
    req = required_glossary_symbols_from_signature(sig)
    text = Path(glossary_path).read_text(encoding="utf-8")
    return check_glossary_structure(
        text,
        required_symbols=req,
        rules_text=rules_text,
        domain_notes=domain_notes,
        inferred_phrase_symbols=inferred_phrase_symbols,
    )
