"""Run ``policy_check`` on every ``.lp`` under a directory; write a JSON array."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]  # asp/asp_pipeline/ -> repo root
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT = _REPO / "bundles" / "asp_from_wfm" / "policies"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Batch asp_pipeline.policy_check on *.lp")
    p.add_argument(
        "--policy-dir",
        type=Path,
        default=_DEFAULT,
        help="Directory to scan (default: bundles/asp_from_wfm/policies).",
    )
    p.add_argument("--out-json", type=Path, default=None, help="Write results JSON to this path.")
    a = p.parse_args(argv)
    d = a.policy_dir.resolve()
    if not d.is_dir():
        print(f"error: {d} not a directory", file=sys.stderr)
        return 2
    from asp_pipeline.policy_check import run_policy_check

    rows: list[dict] = []
    for lp in sorted(d.glob("*.lp")):
        r = run_policy_check(lp)
        r["file"] = str(lp)
        rows.append(r)
    t = json.dumps(rows, indent=2, ensure_ascii=False)
    if a.out_json:
        a.out_json.write_text(t + "\n", encoding="utf-8")
        print(f"Wrote {a.out_json}", flush=True)
    else:
        print(t)
    if any(x.get("status") == "ERROR" for x in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
