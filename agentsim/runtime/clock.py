from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

NowFn = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
