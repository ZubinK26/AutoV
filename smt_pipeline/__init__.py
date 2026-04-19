"""NL→SMT-LIB pipeline (`control_flow_v3.md`)."""

from __future__ import annotations

from typing import Any

__all__ = ["run_smt_pipeline"]


def __getattr__(name: str) -> Any:
    if name == "run_smt_pipeline":
        from .pipeline import run_smt_pipeline

        return run_smt_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
