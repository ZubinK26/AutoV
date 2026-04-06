"""
Registry stage — `pipeline_spec.md` step 3 (Registry agent), Phase 1 pre–formalizer.

Handoff fixtures: `bundles/{bundle_id}.json` (repo root, sibling of `registry_stage/`).
See `development_plan_registry_stage_v1.md`.
"""

from registry_stage.export_session import export_session
from registry_stage.line_driver import (
    LineDriverConfig,
    LineSearchGapsResult,
    build_search_query,
    candidate_covered,
    extract_placeholder_gaps,
    run_search_and_gaps_for_line,
)
from registry_stage.loaders import load_handoff_bundle, load_registry
from registry_stage.models import (
    SCHEMA_VERSION,
    DevSessionSnapshot,
    HandoffBundle,
    HandoffLine,
    RegistryEntry,
    RegistryFile,
    StructuredGap,
)
from registry_stage.registry_session import RegistrySession, validate_session_entry
from registry_stage.semantic_index import (
    BgeFaissSemanticIndex,
    SearchHit,
    StubKeywordSemanticIndex,
    create_semantic_index,
    entry_embed_text,
)
from registry_stage.validation import validate_alignment

__all__ = [
    "SCHEMA_VERSION",
    "BgeFaissSemanticIndex",
    "DevSessionSnapshot",
    "LineDriverConfig",
    "LineSearchGapsResult",
    "StructuredGap",
    "candidate_covered",
    "HandoffBundle",
    "HandoffLine",
    "RegistryEntry",
    "RegistryFile",
    "RegistrySession",
    "SearchHit",
    "build_search_query",
    "extract_placeholder_gaps",
    "StubKeywordSemanticIndex",
    "create_semantic_index",
    "entry_embed_text",
    "export_session",
    "load_handoff_bundle",
    "load_registry",
    "run_search_and_gaps_for_line",
    "validate_alignment",
    "validate_session_entry",
]

__version__ = "0.0.m3"
