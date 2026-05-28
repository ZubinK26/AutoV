"""Mutable Phase 0 chunk state shared with WFM orchestrator (omit / drop)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pivot_wfm.policy_drops import drop_rules_at_global_indices


@dataclass
class PivotChunkWfmContext:
    """
    Per-chunk bridge between ``run_pivot_wfm_until_complete`` and ``run_wfm_registry_e2e``.

    ``chunk_start`` is updated by the pivot loop each chunk. ``retry_chunk`` is set by the
    orchestrator when the operator chooses **omit** at accept (``o``).
    """

    all_rules: list[str]
    work_dir: Path
    chunk_start: int
    rules_per_chunk: int
    progress_path: Path | None = None
    retry_chunk: bool = False
    dropped_any: bool = False
    omitted_global_indices: list[int] = field(default_factory=list)
    active_chunk_end_exclusive: int = 0

    @property
    def chunk_end_exclusive(self) -> int:
        if self.active_chunk_end_exclusive > self.chunk_start:
            return self.active_chunk_end_exclusive
        return min(self.chunk_start + self.rules_per_chunk, len(self.all_rules))

    def begin_chunk(self, start: int, end_exclusive: int) -> None:
        """Set the current chunk span (``end_exclusive`` is global, exclusive)."""
        self.chunk_start = start
        self.active_chunk_end_exclusive = end_exclusive
        self.omitted_global_indices = []

    def drop_local_1based(
        self,
        local_indices: list[int],
        *,
        reason: str,
        bundle_id: str | None = None,
    ) -> list[int]:
        """Map chunk-local 1..N line numbers to global indices and drop from ``all_rules``."""
        if not local_indices:
            raise ValueError("omit requires at least one chunk line index")
        global_ix = [self.chunk_start + int(i) - 1 for i in local_indices]
        end = self.active_chunk_end_exclusive or self.chunk_end_exclusive
        for gi in global_ix:
            if gi < self.chunk_start or gi >= end:
                raise ValueError(
                    f"omit line {gi - self.chunk_start + 1} is outside current chunk "
                    f"(rules {self.chunk_start + 1}–{end} of {len(self.all_rules)})"
                )
        dropped = drop_rules_at_global_indices(
            self.all_rules,
            global_ix,
            work_dir=self.work_dir,
            reason=reason,
            bundle_id=bundle_id,
            chunk_rule_index_start=self.chunk_start,
            chunk_rule_index_end=end,
        )
        self.dropped_any = True
        self.omitted_global_indices.extend(dropped)
        self.active_chunk_end_exclusive = end - len(dropped)
        self._sync_progress_hash()
        return dropped

    def _sync_progress_hash(self) -> None:
        if not self.progress_path or not self.progress_path.is_file():
            return
        import hashlib
        import json

        from wfm_orchestration.nl_chunk_smt_policy_pipeline import (
            NlChunkSmtProgress,
            save_progress,
        )

        eff = self.work_dir / "pivot_wfm_effective_source.nl"
        if not eff.is_file():
            return
        h = hashlib.sha256()
        with eff.open("rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        raw = json.loads(self.progress_path.read_text(encoding="utf-8"))
        prog = NlChunkSmtProgress.from_dict(raw)
        prog.nl_sha256 = h.hexdigest()
        prog.nl_path_posix = eff.as_posix()
        save_progress(self.progress_path, prog)


__all__ = ["PivotChunkWfmContext"]
