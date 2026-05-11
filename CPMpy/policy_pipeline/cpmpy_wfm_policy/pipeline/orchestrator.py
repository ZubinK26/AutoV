"""Deterministic orchestrator: formalize → verify → emit policy (slice 3)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from cpmpy_wfm_policy.llm import FormalizerLLM
from cpmpy_wfm_policy.pipeline.ast_validator import (
    global_constraints_from_namespace,
    load_signature_namespace,
)
from cpmpy_wfm_policy.pipeline.cheap_checks import CheapCheckError, run_routed_cheap_checks
from cpmpy_wfm_policy.pipeline.consistency import ConsistencyError, run_pre_deploy_consistency
from cpmpy_wfm_policy.pipeline.domain_inputs import gated_tool_names, load_tools_json_file
from cpmpy_wfm_policy.pipeline.diagnoser import DiagnoserLLM, diagnose_failure
from cpmpy_wfm_policy.pipeline.few_shot import compose_few_shot_block
from cpmpy_wfm_policy.pipeline.formalizer import (
    FormalizerError,
    FormalizerOutput,
    formalize_one_rule,
    load_formalizer_system_prompt,
    materialize_rule_expression,
)
from cpmpy_wfm_policy.pipeline.repair import fallback_repair_hint
from cpmpy_wfm_policy.verification.medium_checks import MediumCheckError, run_cumulative_model_sat, run_hypothesis_smoke_pattern_a
from cpmpy_wfm_policy.verification.roundtrip import run_roundtrip_one_rule


class OrchestratorState(str, Enum):
    LOAD_INPUTS = "LOAD_INPUTS"
    FORMALIZE = "FORMALIZE"
    REPAIR = "REPAIR"
    BATCH_VERIFY = "BATCH_VERIFY"
    FULL_VERIFY = "FULL_VERIFY"
    CONSISTENCY_CHECK = "CONSISTENCY_CHECK"
    EMIT_POLICY = "EMIT_POLICY"
    RUNTIME_READY = "RUNTIME_READY"


def _log_jsonl(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_per_rule_fixtures(
    fixtures_path: Path,
) -> dict[str, list[tuple[dict[str, int | bool], bool]]] | None:
    if not fixtures_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("per_rule_fixtures", fixtures_path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    raw = getattr(mod, "PER_RULE_FIXTURES", None)
    if raw is None:
        return None
    return dict(raw)


@dataclass
class OrchestratorConfig:
    tool_name: str = "apply_refund"
    max_repairs_per_rule: int = 2
    system_prompt_formalizer: str | None = None
    copy_signature_to_out: bool = True
    #: Cumulative SAT every N rules after cheap checks; ``0`` = only once at end. ``None`` → ``CPMPY_MEDIUM_BATCH_SIZE`` (default 5).
    medium_batch_size: int | None = None
    #: Hypothesis draws for Pattern-A smoke; ``0`` disables. ``None`` → ``CPMPY_MEDIUM_HYPOTHESIS_EXAMPLES`` (default 100).
    medium_hypothesis_examples: int | None = None
    back_translator_llm: FormalizerLLM | None = None
    roundtrip_solver: str | None = None
    consistency_solver: str | None = None
    #: When True (default), run round-trip verification using ``back_translator_llm`` or the same client as the formalizer.
    enable_roundtrip: bool = True
    roundtrip_diagnoser_llm: DiagnoserLLM | None = None
    system_prompt_back_translator: str | None = None
    system_prompt_roundtrip_diagnoser: str | None = None
    max_roundtrip_diagnose_cycles: int = 2
    #: Retries for JSON/schema validation **within** one formalizer call before repair state.
    max_llm_json_retries: int = 3


@dataclass
class OrchestratorResult:
    success: bool
    states: list[str]
    outputs: list[FormalizerOutput] = field(default_factory=list)
    out_dir: Path = field(default_factory=Path)
    error: str | None = None


def _routing_pattern(out: FormalizerOutput) -> Literal["A", "B"]:
    if out.uses_global_constraints or out.uses_vector_variables:
        return "B"
    return "A"


def emit_policy_py(
    *,
    outputs: list[FormalizerOutput],
    dest: Path,
    signature_filename: str = "signature.py",
) -> None:
    """Write importable ``policy.py`` that loads ``signature_filename`` from the same directory."""
    rule_json_inner = json.dumps([o.rule_module for o in outputs])
    lines: list[str] = [
        '"""Generated policy module (cpmpy_wfm_policy orchestrator)."""',
        "from __future__ import annotations",
        "",
        "import importlib.util",
        "import json",
        "from pathlib import Path",
        "",
        f"_RULE_MODULES = json.loads({json.dumps(rule_json_inner)})",
        "",
        "_dir = Path(__file__).resolve().parent",
        f'_spec = importlib.util.spec_from_file_location("domain_signature", _dir / "{signature_filename}")',
        "if _spec is None or _spec.loader is None:",
        '    raise ImportError("cannot load signature.py")',
        "_sig = importlib.util.module_from_spec(_spec)",
        "_spec.loader.exec_module(_sig)",
        "_ns = {k: v for k, v in vars(_sig).items() if not k.startswith('_')}",
        "for i, _src in enumerate(_RULE_MODULES, start=1):",
        '    exec(compile(_src, f"<rule_{i}>", "exec"), _ns, _ns)',
        "",
    ]
    for o in outputs:
        lines.append(f"{o.rule_name} = _ns[{o.rule_name!r}]")
    lines.extend(["", "", "def all_rules() -> dict[str, object]:", "    return {"])
    for o in outputs:
        lines.append(f'        "{o.rule_name}": {o.rule_name},')
    lines.append("    }")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit_manifest(
    *,
    outputs: list[FormalizerOutput],
    nl_lines: list[str],
    dest: Path,
    policy_version: str,
) -> None:
    rules = []
    for o, nl in zip(outputs, nl_lines, strict=True):
        rules.append(
            {
                "id": o.rule_name,
                "rule_index": o.rule_index,
                "nl_source": nl,
                "uses_global_constraints": o.uses_global_constraints,
                "uses_vector_variables": o.uses_vector_variables,
                "pattern": _routing_pattern(o),
                "used_symbols": sorted(o.used_symbols),
                "claimed_dependencies": sorted(o.claimed_dependencies),
            }
        )
    blob = {
        "schema_version": "cpmpy_policy_manifest_v1",
        "policy_version": policy_version,
        "rules": rules,
    }
    dest.write_text(json.dumps(blob, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def emit_consistency_report(
    *,
    body: dict[str, Any],
    policy_version: str,
    dest: Path,
) -> None:
    blob: dict[str, Any] = {
        "schema_version": "cpmpy_consistency_report_v1",
        "policy_version": policy_version,
    }
    blob.update(body)
    dest.write_text(json.dumps(blob, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _content_hash(outputs: list[FormalizerOutput], nl_lines: list[str]) -> str:
    h = hashlib.sha256()
    for nl in nl_lines:
        h.update(nl.encode("utf-8"))
        h.update(b"\n")
    for o in outputs:
        h.update(o.rule_module.encode("utf-8"))
    return h.hexdigest()[:16]


def run_orchestrator(
    *,
    domain_dir: Path,
    out_dir: Path,
    formalizer_llm: FormalizerLLM,
    diagnoser_llm: DiagnoserLLM | None = None,
    cfg: OrchestratorConfig | None = None,
) -> OrchestratorResult:
    cfg = cfg or OrchestratorConfig()
    states: list[str] = []
    log_path = out_dir / "verification_log.jsonl"
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if log_path.is_file():
        log_path.unlink()

    def log_event(event: str, **data: Any) -> None:
        _log_jsonl(log_path, {"ts": _utc(), "event": event, **data})

    states.append(OrchestratorState.LOAD_INPUTS.value)
    log_event("state_enter", state=OrchestratorState.LOAD_INPUTS.value)

    domain_dir = domain_dir.resolve()
    rules_path = domain_dir / "rules.txt"
    sig_path = domain_dir / "signature.py"
    gloss_path = domain_dir / "glossary.md"
    if not rules_path.is_file():
        return OrchestratorResult(False, states, [], out_dir, f"missing {rules_path}")
    if not sig_path.is_file():
        return OrchestratorResult(False, states, [], out_dir, f"missing {sig_path}")
    if not gloss_path.is_file():
        return OrchestratorResult(False, states, [], out_dir, f"missing {gloss_path}")

    tools_path = domain_dir / "tools.json"
    if not tools_path.is_file():
        return OrchestratorResult(False, states, [], out_dir, f"missing {tools_path}")
    try:
        tools_bundle = load_tools_json_file(tools_path)
    except Exception as e:
        return OrchestratorResult(False, states, [], out_dir, f"invalid tools.json: {e}")

    raw_lines = rules_path.read_text(encoding="utf-8").splitlines()
    nl_lines = [ln.strip() for ln in raw_lines if ln.strip() and not ln.strip().startswith("#")]
    fixtures_map = load_per_rule_fixtures(domain_dir / "fixtures" / "per_rule.py")

    sig_s = str(sig_path)
    gloss_s = str(gloss_path)
    sys_fp = cfg.system_prompt_formalizer or load_formalizer_system_prompt()
    outputs: list[FormalizerOutput] = []

    states.append(OrchestratorState.FORMALIZE.value)
    log_event("state_enter", state=OrchestratorState.FORMALIZE.value)

    for i, nl in enumerate(nl_lines, start=1):
        repair_hint: str | None = None
        last_err = ""
        for attempt in range(cfg.max_repairs_per_rule + 1):
            if repair_hint is not None:
                states.append(OrchestratorState.REPAIR.value)
                log_event("state_enter", state=OrchestratorState.REPAIR.value)
            log_event("formalize_attempt", rule_index=i, attempt=attempt, has_repair_hint=repair_hint is not None)
            try:
                fs_block = compose_few_shot_block(
                    rule_index=i,
                    prior_outputs=outputs,
                    prior_nl_lines=nl_lines[: i - 1],
                )
                out = formalize_one_rule(
                    nl_rule=nl,
                    rule_index=i,
                    signature_path=sig_s,
                    glossary_path=gloss_s,
                    llm=formalizer_llm,
                    tool_name=cfg.tool_name,
                    system_prompt=sys_fp,
                    repair_hint=repair_hint,
                    few_shot_examples_block=fs_block,
                    log_event=log_event,
                    max_llm_json_retries=cfg.max_llm_json_retries,
                )
                outputs.append(out)
                log_event("formalize_ok", rule_index=i, rule_name=out.rule_name)
                break
            except FormalizerError as e:
                last_err = str(e)
                if attempt >= cfg.max_repairs_per_rule:
                    return OrchestratorResult(
                        False,
                        states,
                        outputs,
                        out_dir,
                        f"rule {i} formalize failed after {attempt + 1} attempts: {last_err}",
                    )
                if diagnoser_llm is None:
                    repair_hint = fallback_repair_hint(last_err)
                else:
                    d = diagnose_failure(
                        raw_error=last_err,
                        rule_nl=nl,
                        rule_index=i,
                        llm=diagnoser_llm,
                    )
                    repair_hint = d.formalizer_hint
                    log_event("diagnosis", rule_index=i, failure_class=d.failure_class)
            except Exception as e:
                return OrchestratorResult(False, states, outputs, out_dir, f"rule {i}: {e}")

    states.append(OrchestratorState.BATCH_VERIFY.value)
    log_event("state_enter", state=OrchestratorState.BATCH_VERIFY.value)

    gc = global_constraints_from_namespace(load_signature_namespace(sig_s))

    materialized: list[Any] = []
    batch_n = cfg.medium_batch_size
    if batch_n is None:
        batch_n = int(os.environ.get("CPMPY_MEDIUM_BATCH_SIZE", "5"))

    for idx, o in enumerate(outputs):
        pat = _routing_pattern(o)
        expr = materialize_rule_expression(o, sig_s)
        materialized.append(expr)
        fixtures = None
        if fixtures_map and o.rule_name in fixtures_map:
            fixtures = fixtures_map[o.rule_name]
        try:
            run_routed_cheap_checks(
                expr,
                pattern=pat,
                global_constraints=gc,
                fixtures=fixtures,
                run_nontrivial=True,
            )
            log_event("cheap_check_ok", rule=o.rule_name, pattern=pat)
        except CheapCheckError as e:
            return OrchestratorResult(
                False, states, outputs, out_dir, f"cheap_check {o.rule_name}: {e}"
            )

        if batch_n > 0 and (idx + 1) % batch_n == 0:
            try:
                run_cumulative_model_sat(materialized, gc)
                log_event("medium_cumulative_sat_ok", phase="batch", n_rules=len(materialized))
            except MediumCheckError as e:
                return OrchestratorResult(
                    False, states, outputs, out_dir, f"medium cumulative SAT: {e}"
                )

    if materialized:
        need_final = batch_n <= 0 or (len(materialized) % batch_n != 0)
        if need_final:
            try:
                run_cumulative_model_sat(materialized, gc)
                log_event("medium_cumulative_sat_ok", phase="final", n_rules=len(materialized))
            except MediumCheckError as e:
                return OrchestratorResult(
                    False, states, outputs, out_dir, f"medium cumulative SAT: {e}"
                )

    hyp_n = cfg.medium_hypothesis_examples
    if hyp_n is None:
        hyp_n = int(os.environ.get("CPMPY_MEDIUM_HYPOTHESIS_EXAMPLES", "100"))
    if hyp_n > 0:
        rules_a: dict[str, Any] = {}
        for o, ex in zip(outputs, materialized, strict=True):
            if _routing_pattern(o) == "A":
                rules_a[o.rule_name] = ex
        if rules_a:
            try:
                from cpmpy_wfm_policy.verification.hypothesis_generators import flat_state_strategy

                strat = flat_state_strategy(load_signature_namespace(sig_s))
                run_hypothesis_smoke_pattern_a(
                    rules_a, state_strategy=strat, num_examples=hyp_n
                )
                log_event("medium_hypothesis_smoke_ok", n_examples=hyp_n, n_rules=len(rules_a))
            except ImportError as e:
                return OrchestratorResult(
                    False,
                    states,
                    outputs,
                    out_dir,
                    f"medium hypothesis smoke requires 'hypothesis' package: {e}",
                )

    states.append(OrchestratorState.FULL_VERIFY.value)
    log_event("state_enter", state=OrchestratorState.FULL_VERIFY.value)

    if cfg.enable_roundtrip:
        bt_llm = cfg.back_translator_llm or formalizer_llm
        rt_diagnoser = cfg.roundtrip_diagnoser_llm or diagnoser_llm

        def bt_logged(*, system_instruction: str, user_text: str) -> str:
            t0 = time.perf_counter()
            out = bt_llm(system_instruction=system_instruction, user_text=user_text)
            log_event(
                "llm_call",
                role="back_translator",
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            )
            return out

        for o, nl, expr in zip(outputs, nl_lines, materialized, strict=True):
            fs_rt = compose_few_shot_block(
                rule_index=o.rule_index,
                prior_outputs=outputs[: o.rule_index - 1],
                prior_nl_lines=nl_lines[: o.rule_index - 1],
            )
            rt = run_roundtrip_one_rule(
                orig_out=o,
                orig_expr=expr,
                nl_original=nl,
                formalizer_llm=formalizer_llm,
                back_translator_llm=bt_logged,
                signature_path=sig_s,
                glossary_path=gloss_s,
                tool_name=cfg.tool_name,
                system_formalizer=sys_fp,
                system_back_translator=cfg.system_prompt_back_translator,
                roundtrip_solver=cfg.roundtrip_solver,
                diagnoser_llm=rt_diagnoser,
                system_roundtrip_diagnoser=cfg.system_prompt_roundtrip_diagnoser,
                max_diagnose_cycles=cfg.max_roundtrip_diagnose_cycles,
                few_shot_examples_block=fs_rt,
            )
            log_data: dict[str, Any] = {
                "rule": o.rule_name,
                "ok": rt.equivalent,
                "detail": rt.detail,
                "nl_source": nl,
                "nl_back_translation": rt.nl_roundtrip,
                "orig_rule_module": o.rule_module,
            }
            if rt.reform is not None:
                log_data["reform_rule_module"] = rt.reform.rule_module
                log_data["reform_used_symbols"] = sorted(rt.reform.used_symbols)
            if rt.diagnosis is not None:
                log_data["diagnosis_category"] = rt.diagnosis.category
                log_data["diagnosis_strategy"] = rt.diagnosis.repair_strategy
            log_event("roundtrip", **log_data)
            if not rt.equivalent:
                return OrchestratorResult(
                    False,
                    states,
                    outputs,
                    out_dir,
                    f"roundtrip {o.rule_name}: {rt.detail}",
                )
    else:
        log_event("roundtrip", status="skipped_enable_roundtrip_false")

    policy_version = _content_hash(outputs, nl_lines)

    states.append(OrchestratorState.CONSISTENCY_CHECK.value)
    log_event("state_enter", state=OrchestratorState.CONSISTENCY_CHECK.value)
    try:
        cons_body = run_pre_deploy_consistency(
            rule_exprs=materialized,
            rule_ids=[o.rule_name for o in outputs],
            global_constraints=gc,
            gated_tools=gated_tool_names(tools_bundle),
            solver=cfg.consistency_solver,
        )
    except ConsistencyError as e:
        return OrchestratorResult(False, states, outputs, out_dir, str(e))

    for msg in cons_body.get("warnings", []):
        log_event("consistency_warning", message=msg)
    log_event(
        "consistency_ok",
        joint_sat=cons_body["joint_sat"],
        has_coverage=cons_body.get("coverage") is not None,
    )

    states.append(OrchestratorState.EMIT_POLICY.value)
    log_event("state_enter", state=OrchestratorState.EMIT_POLICY.value)

    emit_policy_py(outputs=outputs, dest=out_dir / "policy.py")
    emit_manifest(
        outputs=outputs,
        nl_lines=nl_lines,
        dest=out_dir / "manifest.json",
        policy_version=policy_version,
    )
    emit_consistency_report(
        body=cons_body,
        policy_version=policy_version,
        dest=out_dir / "consistency_report.json",
    )
    if cfg.copy_signature_to_out:
        shutil.copy2(sig_path, out_dir / "signature.py")
    log_event("emit", policy_py="policy.py", manifest="manifest.json", consistency_report="consistency_report.json")

    states.append(OrchestratorState.RUNTIME_READY.value)
    log_event("state_enter", state=OrchestratorState.RUNTIME_READY.value)

    return OrchestratorResult(True, states, outputs, out_dir, None)
