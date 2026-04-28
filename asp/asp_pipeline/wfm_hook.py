"""
Run ClinCon/ASP formalization after a WFM e2e run (``demo_launcher`` / ``wfm_orchestration.cli``).
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from dataclasses import replace
from pathlib import Path
from typing import Any

from asp_pipeline.config import asp_config_from_env
from asp_pipeline.pipeline import run_asp_pipeline


def resolve_handoff_path(
    session: Any,
    args: Namespace,
    repo_root: Path,
) -> Path | None:
    h = getattr(args, "handoff", None)
    if h is not None and Path(h).is_file():
        return Path(h).resolve()
    if getattr(args, "no_handoff_save", False):
        return None
    if session is None or getattr(session, "bundle", None) is None:
        return None
    bid = session.bundle.bundle_id
    from wfm_orchestration.handoff_artifacts import handoff_write_path

    return handoff_write_path(
        repo_root,
        bid,
        handoff_dir=getattr(args, "handoff_dir", None),
    ).resolve()


def _bundle_id_from_path(hp: Path) -> str:
    d = json.loads(hp.read_text(encoding="utf-8"))
    b = d.get("bundle_id")
    if not b:
        raise ValueError("missing bundle_id in handoff")
    return str(b)


def run_asp_formalize_after_wfm(
    *,
    session: Any,
    args: Namespace,
    repo_root: Path,
) -> int:
    """
    Run ``run_asp_pipeline`` on the handoff from ``--handoff`` or the last WFM write.
    Returns shell exit: 0 success, 1 pipeline failure, 2 configuration / missing file.
    """
    h_opt = getattr(args, "handoff", None)
    if h_opt and Path(h_opt).is_file():
        hp = Path(h_opt).resolve()
    else:
        hp = resolve_handoff_path(session, args, repo_root)
    if hp is None or not hp.is_file():
        print(
            "error: cannot resolve handoff JSON for formalization. "
            "Pass --handoff, or ensure WFM saved a handoff (omit --no-handoff-save).",
            file=sys.stderr,
        )
        return 2
    if session is not None and getattr(session, "bundle", None) is not None:
        bid = session.bundle.bundle_id
    else:
        try:
            bid = _bundle_id_from_path(hp)
        except (json.JSONDecodeError, ValueError, OSError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    default_pol = repo_root / "bundles" / "asp_from_wfm" / "policies" / f"{bid}.lp"
    default_out = repo_root / "bundles" / "asp_from_wfm"
    pol = Path(getattr(args, "asp_policy", None) or default_pol).resolve()
    out = Path(getattr(args, "asp_bundle_out", None) or default_out).resolve()
    pol.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    cfg = asp_config_from_env()
    fp = getattr(args, "asp_formalizer_prompt", None) or None
    if isinstance(fp, str) and fp.strip():
        cfg = replace(cfg, formalizer_prompt=fp.strip())
    res = run_asp_pipeline(
        handoff_path=hp,
        policy_model_path=pol,
        bundle_out_dir=out,
        cfg=cfg,
    )
    line = {
        "asp_formalize": True,
        "status": res.status,
        "policy_model_path": res.policy_model_path,
        "bundle_record_path": res.bundle_record_path,
        "log_path": res.log_path,
    }
    print("\n" + json.dumps(line, indent=2, ensure_ascii=False) + "\n", flush=True)
    return 0 if res.status == "success" else 1
