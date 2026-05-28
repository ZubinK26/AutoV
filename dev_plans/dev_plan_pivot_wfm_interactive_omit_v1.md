# Dev plan: Pivot WFM interactive omit (continue without restart)

**Status:** Implemented (v1 — `o` at accept, shared `policy_drops`, resume via `pivot_wfm_effective_source.nl`)  
**Priority:** P1 (operator UX / recruitment-scale policies)  
**Related:** `dev_plan_pivot_wfm_coverage_repair_v1.md` (per-chunk `[d]` drop — implemented but disconnected from WFM accept/omit), `dev_plan_pre_wfm_scope_rewriter_v1.md`

---

## 1. Problem statement

Operators running `python -m pivot_pipeline` hit **OUT_OF_SCOPE** lines during Phase 0 WFM. They want to **omit** those rules (not operationalizable / not objective enough) and **continue the same run** toward `phase0_normalized_nl.txt` without:

- accepting `Y` and then failing **chunk coverage** (`forward=4`, `missing=[4]`),
- guessing the **`n` → disagree → omit** choreography (and crashing if rewrite text is pasted into the indices prompt),
- editing `scope_rewriter/latest.nl` + **`--reset-progress`** mid-run,
- or aborting knowing a later gate will fail.

Today:

| Step | Behavior | Gap |
|------|----------|-----|
| Advisory OOS rewrite | Shown before accept | **Not applied** on `Y` |
| `Y` on package with OUT_OF_SCOPE | Handoff retains `OUT_OF_SCOPE` rows | Pivot coverage requires **PASS/REWRITE** per chunk index → **exit 3** |
| `n` → disagree + omit | Agent 4 merge; pass 2 re-run | **Disagree is mandatory**; omit removes lines from **merged Agent 1 input only** |
| Pass 2 accept + coverage | `analyze_chunk_handoff_coverage` vs **original** `all_rules[start:end)` | **Still expects omitted source indices** → fails again |
| `[d]` drop (interactive-policy) | Pops lines from in-memory `all_rules` | Only after coverage fail menu; **not wired to WFM omit** |

**User intent (correct):** WFM Phase 0 is an **interactive compiler** from scope-rewriter NL → **processed NL** (`phase0_normalized_nl.txt`). Omitted rules should disappear from that product **and** from the in-run policy slice, with audit trail, **without** restarting Phase 0 from rule 0 unless the operator chooses a full reset.

---

## 2. NL artifact truth (answer: critics do not use `latest.nl`)

After Phase 0 completes, downstream pivot phases use artifacts under **`--work-dir`**, not `scope_rewriter/.../latest.nl`:

| Artifact | Written when | Used by |
|----------|--------------|---------|
| `scope_rewriter/latest.nl` | Pre-WFM scope rewriter | **`--input` to Phase 0 only** (chunk source + `nl_sha256` in progress) |
| `wfm_handoffs/*.json` | Each committed chunk | Aggregate, audit, optional replay |
| **`phase0_normalized_nl.txt`** | Post-aggregate (forward `statement_nl` only) | **Extract**, precheck, registry pass, **tester**, **semantic critic** (effective NL) |
| `rules_source.txt` | Copy of `phase0_normalized_nl` (or skip-phase0 path) | Convenience / replay |
| `rules_extracted.json` | Phase 1 extract | Compile, Z3, repairer |
| **`synthetic_en.md`** | Backtranslate from compiled meta-scheme | **Semantic critic** (vs effective NL) |
| `assessment_linearized.txt` / linearized views | Post-compile | **Tester**, cross-critic |

**Semantic critic** (`critic_agent.py` / `semantic_critic_loop.py`): compares **`phase0_normalized_nl` (effective NL)** to **`synthetic_en.md`**, not `latest.nl`.

**Tester:** processed NL vs linearized IR (`run_tester.py` help text: `phase0_normalized_nl.txt` or `rules_source.txt`).

**Implication:** Omitting at WFM must update the **in-run source slice** (`all_rules` / effective source) so aggregate + count gate + extract all see a **consistent smaller** policy. Editing only handoffs or only `latest.nl` without progress sync is insufficient.

---

## 3. Goals (acceptance criteria)

### G1 — Omit at confirmation (primary UX)

At `Accept entire confirmation package for registry handoff? [Y/n/o]:` (new token):

- **`o` / `omit`** (and optional synonyms): enter **omit-only sub-flow** without requiring a fake “disagree” index.
- Prompt: `OUT_OF_SCOPE line indices to omit from policy (chunk 1-based, comma-separated):`
- Optional: `Also omit PASS lines? [y/N]` default **N** (only OOS by default).
- System **records drops**, **does not write** a failing handoff as the committed chunk artifact (or writes a handoff marked `omitted` that coverage treats as satisfied — see G2).

### G2 — Coverage respects omissions in the same run

When operator omits chunk-local line(s) `k,…`:

1. Remove global indices `(start + k - 1)` from in-memory `all_rules` (same as today’s `[d]` drop).
2. Append to `pivot_wfm_dropped_rules.jsonl` with `reason: "operator_omit_wfm_confirm"`, `bundle_id`, original text, Agent 3 scope report.
3. **Shrink chunk span** for coverage: expected indices = current `all_rules[start:chunk_end)` after drop, **not** the pre-omit span.
4. Either:
   - **(Preferred)** Skip WFM re-run for omitted-only confirmation: commit a **synthetic chunk record** that maps remaining indices to next handoff attempt; **or**
   - Re-run WFM on shortened chunk (fewer lines) and require PASS/REWRITE for **all remaining** lines only.
5. Advance `next_rule_index` only when remaining chunk lines are forward-covered.
6. Maintain `pivot_wfm_effective_source.nl` incrementally (join of `all_rules` after any drop in Phase 0).

### G3 — Integrate with existing `n` / Agent 4 path

- **`n` + disagree + omit** continues to work; omit set must also apply **G2** drops on pass 2 accept (not only merge text shrink).
- If operator **disagrees** line 2 and **omits** line 2, Agent 4 patch for line 2 is skipped (already in `style_a_merge`); on accept, **G2** must still remove global rule 2 from `all_rules`.

### G4 — Post–Phase 0 gates stay coherent

- `aggregate_pivot_wfm_nl`: only forward lines (unchanged); blocking OUT_OF_SCOPE rows must not appear in committed handoffs once omit path used.
- `enforce_wfm_rule_coverage`: compare `wfm_nl_text` to **`pivot_wfm_effective_source.nl`** when drops occurred (already partially implemented in `run.py`); ensure omit-at-confirm updates effective source **before** final gate.
- Run summary fields: `wfm_dropped_rule_count`, `wfm_dropped_reasons[]`, `user_consented_wfm_incomplete_coverage` only when count mismatch without drops.

### G5 — No forced run abort for “known future failure”

- Non-interactive default may remain strict (exit 3), but **`--interactive-policy`** (or new **`--interactive-wfm`**) should make omit path reachable and chunk commit succeed.
- Document: recruitment-scale runs should pass **`--interactive-policy`** until omit UX is default for TTY.

### G6 — Resume without `--reset-progress` after omit

- `nl_chunk_progress.json` must stay consistent: `next_rule_index`, `nl_sha256` of **effective** source or store `nl_sha256_effective` + `dropped_indices[]` in progress sidecar.
- **Do not** require editing `latest.nl` for omit; optional: write-back `scope_rewriter/latest.nl` only on explicit `--sync-scope-rewriter` flag.

---

## 4. Non-goals (v1)

- Changing Agent 3 scope contract (still flags open-ended “another …”).
- Auto-omitting without operator confirmation.
- NagV SMT / registry formalizer omit semantics (pivot profile only).
- Rewriting scope rewriter to pre-split enumerations (separate hardening).

---

## 5. Proposed design

### 5.1 Confirmation state machine (orchestrator)

```
Accept? 
  Y  → snapshot from A3 verdicts → handoff → return to pivot coverage check
  n  → disagree/comment → omit? → A4 → pass 2 → Accept? → ...
  o  → omit_indices → apply_policy_drops() → shortened chunk WFM OR commit omit audit + retry chunk
```

`apply_policy_drops(omit_local_1based, *, chunk_start, all_rules, work_dir)` lives in **`pivot_wfm/policy_drops.py`** (new), shared by orchestrator callback and `run_wfm_phase.py` `[d]` menu.

### 5.2 Pivot ↔ orchestrator contract

Extend `run_wfm_registry_e2e` return value or add optional **`on_before_handoff_commit`** hook:

```python
# pivot_wfm/run_wfm_phase.py after run_wfm_registry_e2e returns
if dev and not coverage_ok:
    if operator_omitted_this_chunk:
        apply drops + retry (no exit 3)
```

Cleaner: pass **`mutable_chunk_state: ChunkWfmState`** into orchestrator:

- `source_rules: list[str]`  # global all_rules slice refs
- `global_start: int`
- `dropped_log: Path`

Orchestrator **omit** path calls `chunk_state.drop_local_indices([2,4])` before pass 2 or instead of failed accept.

### 5.3 Handoff / audit model

Add optional per-line field in handoff JSON:

```json
{ "line_index": 23, "agent3_verdict": "OMITTED", "statement_nl": "<original>", "omit_reason": "operator_confirm", "scope_report": "..." }
```

Coverage: **`OMITTED` does not count as forward** and **does not count as missing** if global index was removed from `all_rules`. For committed handoffs that still store omitted rows for audit, coverage filter excludes indices present in `chunk_omitted_indices` set on the chunk record.

Extend `nl_chunk_progress.chunk_records[]`:

```json
{
  "chunk_seq": 2,
  "rule_index_start": 10,
  "rule_index_end": 15,
  "omitted_global_indices": [12],
  "bundle_id": "..."
}
```

### 5.4 UX hardening (quick wins, same PR)

| Issue | Fix |
|-------|-----|
| Paste rewrite into indices prompt | `_parse_int_list`: if any token non-int, print error and **re-prompt** (do not traceback) |
| Accept prompt unclear | Footer: `Y=accept as-is  n=disagree/A4  o=omit OUT_OF_SCOPE lines and continue` |
| Advisory rewrite misleading | Prefix: `Not applied unless you disagree (n) or edit source NL` |

### 5.5 Default interactive mode (optional)

`run_pivot_pipeline`: if `sys.stdin.isatty()` and profile env `PIVOT_WFM_INTERACTIVE_DEFAULT=1`, set `interactive_policy=True` for Phase 0 only.

---

## 6. Implementation phases

### Phase A — Shared drop primitive (1–2 days)

- [ ] `pivot_wfm/policy_drops.py`: `drop_rules_at_indices(all_rules, indices) -> list[str]`, JSONL append, effective source write helper.
- [ ] Refactor `run_wfm_phase.py` `[d]` menu to call helper.
- [ ] Unit tests: index pop order, global index math, effective source content.

### Phase B — Orchestrator omit path (2–3 days)

- [ ] `wfm_orchestration/orchestrator.py`: `o` branch, omit-only without disagree; re-prompt safe `_parse_int_list`.
- [ ] Wire `ChunkWfmState` from `run_pivot_wfm_until_complete` (pass `all_rules`, `start`, `work_dir`, `input_fn`).
- [ ] On omit confirm: drop globals, rebuild `chunk_text` from shortened slice, **continue same outer pass** or immediate re-call WFM with `auto_accept=False` for shortened chunk only.
- [ ] Tests: mock `input_fn` sequence `o` → `2` → … → coverage OK.

### Phase C — Coverage + progress alignment (1–2 days)

- [ ] `handoff_coverage.analyze_chunk_handoff_coverage(..., omitted_indices=frozenset())`.
- [ ] `commit_chunk_record` stores `omitted_global_indices`.
- [ ] Progress sidecar: `effective_nl_sha256` after drops; reload uses effective rules for chunking when `pivot_wfm_effective_source.nl` exists.
- [ ] Aggregate: skip blocking rows for indices already in drop log.

### Phase D — Gates, docs, CLI (1 day)

- [ ] `run_summary.json`: drop counts and omit reasons.
- [ ] `NagV/pivot_pipeline/README.md`: omit flow, artifact table (§2 above).
- [ ] `Extract-Pivot.md` or `ARCHITECTURE.md`: one paragraph on processed NL vs scope rewriter NL.
- [ ] Env: document `PIVOT_WFM_COVERAGE_MAX_WFM_ATTEMPTS` + interactive flag together.

### Phase E — Optional polish

- [ ] `Y` with OUT_OF_SCOPE present: warn + offer `o` sub-prompt before committing failing handoff.
- [ ] Apply advisory suggestion on `y` sub-choice: `Y+s` = accept with suggestions as REWRITE for OOS lines (LLM risk; behind flag).

---

## 7. Test plan

| Test | Type |
|------|------|
| Omit line 2 of 5-line chunk; coverage passes with 4 forward rows | Integration (mock LLM + stdin) |
| `n` + disagree 2 + omit 2 + pass 2 → global `all_rules` len −1 | Integration |
| Non-interactive omit unavailable; exit 3 unchanged | Unit |
| Resume after omit chunk: `next_rule_index` correct, no sha mismatch when effective source tracked | Unit |
| Aggregate + `enforce_wfm_rule_coverage` with 51→50 rules after one omit | Integration |
| Critic still runs on `phase0_normalized_nl` excluding omitted semantics | Manual / fixture |

---

## 8. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Silent policy shrink without audit | Require JSONL drop record + run_summary |
| Committed handoffs reference stale global `line_index` after mid-policy drops | Chunk record stores `omitted_global_indices`; aggregate sorts by index; document index stability |
| Operator omits too much | Confirm prompt lists verbatim lines to drop |
| Agent 4 omit + disagree confusion | Single omit parser; integration test matrix in §7 |
| `latest.nl` out of sync with effective policy | Do not auto-edit; document; optional sync flag |

---

## 9. Operator workflow (target, post-implementation)

```powershell
python -m pivot_pipeline `
  --input NagV\exports\scope_rewriter\...\latest.nl `
  --work-dir NagV\exports\pivot_runs\recruitment_16_temp_wfm `
  --interactive-policy
```

Per chunk, when Agent 3 marks lines OUT_OF_SCOPE:

1. `Accept…?` → **`o`**
2. `Omit lines:` → **`4`** (chunk-local)
3. Pipeline drops global rule, retries or commits shortened chunk, **continues to next chunk**.
4. Phase 0 ends → `phase0_normalized_nl.txt` has **no** omitted rules.
5. Extract / critic / Z3 run on processed NL only — **no** need to touch `latest.nl` or `--reset-progress`.

Resume after crash: same command **without** `--reset-progress` if `nl_chunk_progress.json` + effective source hash align.

---

## 10. Open questions

1. **Re-run WFM after omit?** Omit-only might skip Agent 2/3 for dropped lines (inject forward from raw NL) vs full re-run on shortened chunk — v1 preference: **re-run shortened chunk** for consistency of `statement_nl` style.
2. **Should `OMITTED` appear in `phase0_normalized_nl`?** No — exclude from aggregate input entirely.
3. **PIVOT default interactive?** Product call; dev plan recommends TTY default-on for Phase 0 until omit is stable.

---

## 11. Summary for stakeholder

You are **correct**: downstream formalization and critics should consume **WFM-processed NL**, not scope-rewriter `latest.nl`. The pipeline already intends that via `phase0_normalized_nl.txt`; the bug is that **omit decisions at WFM accept do not yet shrink the in-run policy or satisfy coverage**, so the run fails or forces restart. This plan connects **confirm omit** → **policy drop** → **chunk coverage** → **effective source** → **aggregate** in one continuous run.
