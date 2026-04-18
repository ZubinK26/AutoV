# Dev plan: post-WFM formalization → consolidation → registry (complete workflow)

**Purpose:** Single end-to-end design for this slice of the product. When this plan is **fully implemented**, the **post-WFM** path is **done**: formalize from NL with durable mapping, consolidate symbols, then commit to the registry **without** requiring the formalizer to emit legacy `entry_id` substrings or to interleave NL-first resolve with half-baked Z3.

**Non-goal:** Rewriting WFM itself. **Entry point** is the existing **`HandoffBundle`** (or equivalent snapshot) **immediately after** user acceptance, as in `pipeline_spec.md` / `registry_persistence_v1.md`.

**Relationship to canonical docs:** This file is the **implementation blueprint** until merged into `pipeline_spec.md`; behavior described here **supersedes** informal prior assumptions about “registry before formalization.”

---

## 1. Outcomes (definition of done)

| Outcome | Acceptance test |
|--------|-------------------|
| **Formalization** | Every **in-scope** line has **executable** `z3_python_source`, **one isolated script per line**, Z3 subprocess succeeds (no uncaught exception). **Forbidden:** `print("UNSAT")` / fake solver output unless the script **actually** calls `Solver.check()` and prints **that** result. |
| **NL ↔ code mapping** | Persisted record per `(bundle_id, line_index)`: `statement_nl`, `registry_resolved_nl` **if** produced by legacy resolve (optional copy), **final** `z3_python_source`, **`identifier_notes`**, hashes, timestamps. |
| **Consolidation** | **Exact** + **semantic** retrieval over the **bundle’s** lines; **evaluation** assigns each cluster to **rename-only automation**, **escalation**, or **document-only** dedup; **rename audit log** for every automated change. |
| **Registry** | **Deterministic parse** of **post-consolidation** Z3 produces **symbols**; **M4-style linking** attaches **canonical symbols** to **existing** `entry_id`s where appropriate; **M5-style populate** creates **only** symbols still unmatched. **No** dependency on **substring** `entry_id` presence in source text. |
| **Operability** | One **orchestrated** command (or fixed sequence) from **handoff JSON** → **export** including formalization traces + registry snapshot + consolidation audit. |

---

## 2. Control flow (single ordered pipeline)

```
WFM accept
  → HandoffBundle (frozen)
       → [F1] Formalization (LLM + Z3 gate per line)
       → [F2] Bundle artifact store (filesystem)
       → [C1] Exact index (NL normalize + structural hash per line)
       → [C2] Semantic index (embeddings over NL + short symbol summary)
       → [C3] Pair/cluster generation (within bundle, then registry candidates)
       → [C4] Evaluation engine (scenario matrix §5)
       → [C5] Automated rename applier (only when §6 preconditions hold)
       → [C6] Z3 regression (per line, after renames)
       → [R1] Deterministic parse of final Z3 → `ParsedSymbolTable` per line + bundle union
       → [R2] Symbol–registry linking (retargeted M4: §7)
       → [R3] Populate new entries (retargeted M5: §7)
       → [R4] Persist registry file + `DevSessionSnapshot` + consolidation audit
```

**Blocking:** Any step **fails closed** (explicit `failure_reasons`, no silent stub). **Escalation** items **block** `[R2]` for affected symbols until resolved or **explicitly waived** by policy (human flag in export only—not default).

---

## 3. Artifacts and schemas (concrete)

### 3.1 `FormalizationLineRecord` (per line, post–F1)

| Field | Type | Rule |
|-------|------|------|
| `bundle_id` | str | From handoff |
| `line_index` | int | 0-based, stable |
| `statement_nl` | str | From `HandoffLine.statement_nl` |
| `agent3_verdict` | enum | Copy from handoff; **OUT_OF_SCOPE** → **no** Z3 required |
| `z3_python_source` | str | Must contain `z3.Solver()`, `check()`, and print **real** check result **or** explicit `raise FormalizationError(...)` — **never** fake UNSAT |
| `identifier_notes` | `list[IdentifierNote]` | **Required** for in-scope lines that emit Z3 |
| `z3_exit_code`, `z3_stdout`, `z3_stderr` | | From subprocess |
| `formalization_status` | enum | `ok` \| `failed_z3` \| `failed_llm` \| `skipped_out_of_scope` |
| `source_hash` | str | SHA-256 of `z3_python_source` |

### 3.2 `IdentifierNote` (one per uninterpreted symbol **declared** in source)

| Field | Type | Rule |
|-------|------|------|
| `local_name` | str | Python identifier as used |
| `z3_name_string` | str | String passed to `DeclareSort` / `Function` / `Const` — **must** match the corresponding literal in `z3_python_source` |
| `kind` | enum | `sort` \| `uninterpreted_function` \| `constant` |
| `signature` | str | Canonical text: `Person` (sort), `Man -> Bool`, `Person * Person -> Bool`, etc. — **no** bound variables |
| `nl_phrases` | list[str] | 1–3 short spans from `statement_nl` |
| `design_note` | str | **One sentence**, max 200 chars — why this symbol exists |

**Omitted from registry persistence** (debug export only): `design_note` if team wants zero drift risk; default **keep in dev export**, **strip** from `RegistryFile` entries.

### 3.3 `StructuralKey` (for comparison)

- **Input:** Parse `z3_python_source` with a **restricted** Python AST walker that collects only: `z3.Sort`, `z3.Function`, `z3.Const`, `z3.ForAll`, `z3.Exists`, `z3.And`, `z3.Or`, `z3.Not`, `z3.Implies`, `z3.Eq`, applications, **quantifier-bound names** normalized to **De Bruijn-style placeholders** (`v0`, `v1`, … in order of binding).
- **Output:** Canonical **S-expression string** + **SHA-256** = `structural_hash`.
- **Rename-only equivalence:** Same `structural_hash` after **normalizing** uninterpreted symbol names to placeholders **per declaration order** within the line.

**Implementation note:** If AST parsing is too fragile for LLM code, **fallback** is **execute in sandbox** and introspect Z3 objects (harder); **v1** requirement is **AST path** + **golden tests** on hand-written scripts **before** LLM code is trusted.

### 3.4 `ConsolidationAuditRecord`

- `bundle_id`, `step`, `scenario_id` (E1–E7, Q1–Q4), `lines_involved`, `decision`, `rename_map` (old→new), `structural_hashes`, `embedding_scores`, `escalation_payload` (if any).

---

## 4. Search layer (concrete)

### 4.1 Exact (NL)

- Normalize: **Unicode NFKC**, **lowercase**, **collapse** ASCII whitespace to single spaces, **strip** leading/trailing, **remove** punctuation characters class `[\p{P}\p{S}]` except apostrophe inside words (regex defined in code).
- **Match key** = normalized string.
- **Use:** duplicate NL lines in bundle; **O(n²)** within bundle is acceptable for **n ≤ 200**.

### 4.2 Exact (structure)

- **Match key** = `structural_hash` (§3.3).
- **Use:** duplicate theory, rename-only detection.

### 4.3 Semantic retrieval

- **Corpus text** per line: `normalized_nl + " | " + comma_separated(sorted(local_names from identifier_notes))`.
- **Model (default):** `sentence-transformers` **`all-MiniLM-L6-v2`**, **L2-normalized** vectors, **cosine similarity**.
- **Infrastructure:** **Local** CPU inference in-process; **no** network required for CI. **Optional** override via env `AUTOV_EMBEDDING_BACKEND=openai` + `OPENAI_API_KEY` for production **only** if configured — code must **default** to local.
- **Top-k:** **k = 8** for within-bundle pairs; **k = 20** when querying **registry** candidate entries for **symbol linking** (§7).
- **Threshold:** **Primary** decision is **never** similarity alone. **Semantic** score **≥ 0.82** cosine → **eligible** for **paraphrase gate** (§5.2 E3); **below** → **no** auto merge.

---

## 5. Evaluation engine (scenarios — all paths defined)

### 5.1 Paraphrase gate (LLM, constrained)

- **Trigger:** E3 only (semantic eligible + structural match + rename-only).
- **Input:** Two `statement_nl` strings + one-line **summary** of each `identifier_notes` (kinds + signatures only).
- **Output JSON schema:** `{ "same_proposition": bool, "confidence": float, "reason": str }`
- **Model:** Same stack as formalizer; **temperature 0**; **max tokens** 256.
- **`same_proposition` true** → follow **E1** rename policy. **false** → **E4** (escalate).

### 5.2 Scenario matrix (actions)

| ID | Condition | Action |
|----|-----------|--------|
| **E1** | Exact NL key match + same `structural_hash` + rename-only between lines | **Automated rename** to canonical names per §6. **First line_index wins** among competing lines. |
| **E2** | Exact NL key match + **different** `structural_hash` | **Escalation required** — `escalation_kind: nl_duplicate_theory_mismatch`. **No** registry merge. **Re-formalize** one line after human or constrained fix. |
| **E3** | Semantic ≥ 0.82 + same `structural_hash` + rename-only | Run **paraphrase gate**; on pass → **E1**; on fail → **E4**. |
| **E4** | Semantic ≥ 0.82 + **different** structure **or** failed paraphrase gate | **Escalation** — `escalation_kind: semantic_paraphrase_or_structure`. |
| **E5** | Same `local_name` in two lines, **different** `signature` in `identifier_notes` | **Collision.** Auto-suffix **`_ln{line_index}`** appended to **later line’s** declarations and uses **only if** `structural_hash` differs; **if** structures match, **escalate** (likely copy-paste bug). |
| **E6** | Different NL keys + same `structural_hash` | **Documentation link** only: both `line_index` reference same **`canonical_theory_id`** (UUID) in export; **E1** renames for **identifier** alignment **within** bundle storage. **Single** stored copy of Z3 optional optimization — **not** required for correctness. |
| **E7** | One line `failed_z3` or missing `identifier_notes` | **Exclude** from merge cluster; **pipeline fails** bundle consolidation unless **skip** flag per line (not default). |

### 5.3 Identifier-quality conflicts

| ID | Condition | Action |
|----|-----------|--------|
| **Q1** | “Same” concept per embedding, **different** sorts in signatures | **Escalate** `sort_mismatch`; **no** auto-merge, **no** bridge axioms in this workflow. |
| **Q2** | Same `local_name`, different arity | **E5** path. |
| **Q3** | Predicate `A -> Bool` vs function `A -> B` for same NL phrase | **Escalate** `representation_fork` — human picks **one** representation; **re-formalize** the other line. |
| **Q4** | Constant vs variable confusion (same spelling) | Rare; **escalate** if `structural_hash` differs; else **ignore** bound names (not in `identifier_notes`). |

### 5.4 Escalation handling (concrete)

1. **Automatic:** **Constrained LLM** proposes **one** of: `reformalize_line_indices`, `accept_suffix_rename`, `mark_theory_duplicate` — **must** match JSON schema; **invalid** → human.
2. **Human:** Required for **Q1**, **Q3**, **E2**, **E4** when auto proposal **not** applied within **1** retry.
3. **Queue artifact:** `escalations.json` in bundle export with **blocking** field; orchestrator **exits non-zero** if **blocking** escalations **open** and **no** `--allow-partial-registry` (dev-only flag).

---

## 6. Automated rename (preconditions — all mandatory)

1. **Scenario E1** or **E3** after paraphrase gate **true**.  
2. **Canonical base:** **lowest `line_index`** among the cluster **wins** — its **local** names become **canonical** for that cluster.  
3. **Scope:** **Textual replace** within **`z3_python_source`** for each **affected** line — replace **declaration** and **uses** of **uninterpreted** symbols **listed** in `identifier_notes` (not Python locals unrelated to Z3).  
4. **Regression:** Re-run Z3; **`z3_stdout`** must match **byte-for-byte** vs pre-rename **for that line’s script in isolation** (same `sat`/`unsat` line).  
5. **If regression fails:** **Revert** rename for that cluster, **escalate** `rename_regression_failed`.

**Bound variables:** Never renamed in persisted source; **normalization** for hashing only renames internally.

---

## 7. Legacy registry stage: where M3 / M4 / M5 land

**Today (`bundle_workflow.py`):** per line **search_and_gaps** → **resolve** → **populate_provisional_from_gaps** driven primarily by **NL** and **gap** structure **before** a stable Z3 artifact exists.

**Target:** **NL-first gap/resolve** is **not** the **authoritative** path for symbols that **already** appear in **parsed Z3**. The registry **ingestion** order becomes:

| Legacy | New role |
|--------|-----------|
| **M3 search** | **Split:** (a) **Within-bundle** — already handled in **§4** (exact + semantic on lines). (b) **Registry recall** — for each **`ParsedSymbol`** (from §R1), run **semantic** search over **existing** registry entries’ **NL aliases + prior formalization summaries** (stored when available) to get **candidate** `entry_id`s. **Exact** match on **`signature`** string **first** — if **unique**, **skip** LLM. |
| **M4 resolve** | **Symbol linking:** For each **canonical** `(signature, local_name)` after consolidation, choose **0 or 1** `entry_id` from candidates **or** **new**. Inputs: **NL** lines where symbol appears (from cross-reference index), **candidate** entries, **structured** resolver JSON (reuse **`run_automated_resolve`** patterns **where** applicable) — **prompt** changes from **NL gap** focus to **“link this parsed symbol to registry row.”** |
| **M5 populate** | **Create** entries **only** for symbols **without** a linked `entry_id`. **Fields** populated from **parse** (sort/function/const), **not** from LLM prose. **NL** attachment: **all** `(bundle_id, line_index)` where symbol appears. |

**`run_bundle_through_registry`:** Either **replaced** by **`run_registry_ingestion_post_formalization(bundle, session, parsed_tables, ...)`** or **wrapped**: if **`formalization_artifact_present`** → **new** path; else **legacy** path for **migration** period. **Migration** ends when **all** demos use **F1–C6**; then **legacy** path **deleted**.

**OUT_OF_SCOPE lines:** **No** Z3; **no** parse; **trace-only** in `line_traces` as today.

---

## 8. Formalizer / edge-manifest / committed_edges

- **`committed_edges` / `edge_manifest_ok` substring checks:** **Deprecated** for **go/no-go**. **Replaced** by: **post-parse** **`symbol_used_in_line → entry_id`** edges **computed** from AST + **R2** link table.  
- **Optional retention:** **Debug** mode may **compare** old substring check to **new** edges for **telemetry** during migration.

---

## 9. Filesystem layout (bundle export)

```
exports/formalized_bundles/{bundle_id}/
  handoff.json                 # copy of HandoffBundle
  formalization/
    line_{i}.py                # optional materialized scripts
    line_records.json          # FormalizationLineRecord[]
  consolidation/
    audit.jsonl                # ConsolidationAuditRecord
    structural_index.json
    rename_map.json
    escalations.json           # if any
  registry/
    parsed_symbols.json        # ParsedSymbolTable
    link_table.json            # local → entry_id
    registry_snapshot.json     # RegistryFile
  dev_session.json             # DevSessionSnapshot superset
```

---

## 10. Orchestration changes (concrete)

1. **`wfm_orchestration`:** After **accept**, call **`run_post_wfm_pipeline(handoff, ...)`** instead of **immediate** `run_bundle_through_registry` **unless** `--legacy-registry-first` (default **false** after cutover).  
2. **`DevSessionSnapshot`:** Extend with **`formalization_line_traces`**, **`consolidation_audit`**, **`parsed_symbol_tables`** — **schema version** bump **once** in `registry_stage/models.py`.  
3. **CLI:** `--post-wfm-formalization` **on** by default when implemented; **feature flag** env `AUTOV_POST_WFM_MODE=legacy|new`.

---

## 11. Testing (minimum)

| Test | Assert |
|------|--------|
| Golden Z3 pairs | Rename-only → **same** `structural_hash`. |
| Rename applier | **E1** cluster → **byte-identical** Z3 stdout after rename. |
| Collision E5 | Later line gets suffix; **re-run** Z3 **ok**. |
| Parse | Known script → **expected** `ParsedSymbolTable`. |
| Registry ingestion | Mock session → **link** reuses **existing** entry with **same** signature; **new** symbol → **one** new `entry_id`. |
| Forbidden output | Grep **CI** for `print("UNSAT")` **without** preceding `check()` in formalizer outputs — **fail** build. |

---

## 12. Implementation order (strict)

1. **Schemas** + **Pydantic** (or dataclasses) + **JSON** validators.  
2. **F1** formalizer prompt + subprocess runner + **FormalizationLineRecord** writer.  
3. **F2** bundle store layout.  
4. **C1–C3** indexes + pair generation.  
5. **C4** evaluation + **C5** rename + **C6** regression.  
6. **R1** deterministic parser.  
7. **R2–R3** registry adapter + **migration** flag from legacy `run_bundle_through_registry`.  
8. **Orchestrator** wiring + **export** + **tests**.  
9. **Remove** legacy path + **substring** manifest gate **after** parity demo.

---

## 13. Risk register (short)

| Risk | Mitigation |
|------|------------|
| LLM emits non-AST-parseable Python | Sandboxed **fallback** executor + Z3 introspection **phase 2** if AST failure rate **> 5%** in CI samples. |
| Semantic threshold wrong | **Tune** `0.82` using **labeled** bundle set; **config file** `consolidation.yaml`. |
| Registry duplication across bundles | **R2** **must** query **global** session index; **signature** exact dedup **before** embedding. |

---

*This plan is the **single** specification for post-WFM formalization through registry commit until explicitly superseded by an update to this file or merged `pipeline_spec.md`.*
