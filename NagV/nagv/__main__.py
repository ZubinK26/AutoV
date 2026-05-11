"""Allow ``python -m nagv`` (cwd ``NagV/`` or ``PYTHONPATH`` including ``NagV/``)."""

from __future__ import annotations

import sys
from pathlib import Path

_nagv_dir = Path(__file__).resolve().parent.parent
if str(_nagv_dir) not in sys.path:
    sys.path.insert(0, str(_nagv_dir))

from nagv.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
