# Dev plan: Pivot Tester — processed NL ↔ linearized IR alignment (v1)

## Status

| Area | Status |
|------|--------|
| **Problem statement / role definition** | Done |
| **Prompt rewrite (`tester_pivot_semantic.md`)** | Done |
| **Orchestration (`run.py` — linearize before tester)** | Done |
| **`run_pivot_tester` signature + wiring** | Done |
| **`TesterReport` schema extensions** | Done |
| **Unit tests** | Done |
| **Docs (`ARCHITECTURE.md`, `README.md`)** | Done |
| **Replay on existing work_dir (`run_tester.py`, `pivot-tester`)** | Done |
| **Tester → Repairer interactive loop** | Out of scope v1 (follow-up) |

---

## Problem

Today **`--with-tester`** compares **effective NL** to **`synthetic_en.md`**. Synthetic English is a **deterministic structural index** (rule id, `template_class`, `applies_to`, pathways) — it **does not** expose triggers, thresholds, constants, or consequents. The tester therefore **duplicates pivot critic’s weak axis** and adds little for **rule-content** alignment.

There is **no dedicated stage** that asks: *“Does each processed NL line match what `R000n` actually encodes?”*

**Cross-critic** uses processed NL + linearization but is scoped to **cross-rule IR coherence** (split denial channels, inconsistent consequent slots across rules, preemption interactions). It explicitly **defers** per-line NL↔IR body checks and benign paraphrase to other stages.

**Goal:** Repurpose **Tester** to become the **per-rule NL ↔ formal content** audit, using:

1. **Processed NL** — one policy statement per line (same text as extract / precheck / `rules_source.txt` / `phase0_normalized_nl.txt`, including extract-phase rewrites when present).
2. **Linearized model** — deterministic one-line-per-rule view from `rules_extracted.json` (same output as `linearize_rules_for_cross_critic`).

Tester runs **after precheck, before pivot critic** (unchanged slot). **This ordering is a hard requirement** for v1 — do not move tester after critic or merge the two stages.

---

## Invocation modes (v1 must support both)

### Mode A — Full e2e on **new** NL input

Normal `pivot-pipeline` run with `--with-tester` (and optionally `--with-critic`, etc.):

1. Phase 0 (unless `--skip-phase0`) → extract → compile → Z3 → synthetic → precheck  
2. **Build linearization** from current `rules_extracted.json`  
3. **Tester** (NL ↔ linearized)  
4. **Pivot critic** (only if `--with-critic`)  
5. Later optional stages (cross-critic, templates, …)

When both flags are set, **tester always runs immediately before pivot critic** — same as today’s `--with-tester` placement in `run.py` (after precheck block, before `skip_critic` / semantic critic loop).

### Mode B — **Replay tester only** on an **existing** completed run (on-disk artifacts)

Goal: run the **new** tester against **any eligible existing work_dir** — a policy already formalized e2e **without** re-running WFM, extract, or critic. Typical case: `rules_extracted.json` + processed NL on disk; linearization may be missing and is **regenerated** when tester runs.

**Eligibility** (minimum files in `--work-dir`):

| File | Required | Role |
|------|----------|------|
| `rules_extracted.json` | **Yes** | Source for linearization + compile reload |
| `rules_source.txt` **or** `phase0_normalized_nl.txt` **or** `nl_after_extract_rewrites.txt` | **Yes** (first found, same order as precheck) | Processed NL for tester prompt |
| `meta_scheme.json` | **Yes** | Reload compile path on `--skip-phase0` (existing behavior) |

**Not required** for tester replay: prior `tester_report.json`, `linearized_model_for_cross_critic.txt` (regenerated), `synthetic_en.md`, critic artifacts, Phase 0 progress.

**Implementation — two supported entry paths (both required in v1):**

1. **Main CLI (primary)** — mirror cross-coherence resume pattern:

   ```text
   pivot-pipeline ^
     --input <same nl_source as original run> ^
     --work-dir <existing-work-dir> ^
     --skip-phase0 ^
     --rules-json <work-dir>/rules_extracted.json ^
     --with-tester ^
     --fail-on-tester-findings
   ```

   Omit `--with-critic` so the run **stops after tester** (no pivot critic LLM). Pipeline must still compile/load rules, refresh synthetic/precheck if needed for consistency, then **linearize → tester → write `tester_report.json` → exit** with outcome `ok` or `blocked_tester`.

2. **Thin segment CLI (recommended, parity with `cross_coherence.py`)** — new module e.g. `pivot_pipeline/tester_only.py` or `pivot_pipeline/run_tester.py`:

   ```text
   python -m pivot_pipeline.run_tester ^
     --work-dir <existing-work-dir> ^
     --input <nl_source path from original run>
   ```

   - Defaults: `--rules-json <work-dir>/rules_extracted.json`  
   - Loads processed NL from `work_dir/rules_source.txt` when present, else `phase0_normalized_nl.txt`, else `nl_after_extract_rewrites.txt`, else `--input` resolved file.  
   - Calls shared helper: `build_and_write_linearized(rules)` → `run_pivot_tester(...)` → writes `tester_report.json`, `tester_result.txt` (raw LLM, optional).  
   - **Does not** invoke pivot critic, cross-critic, or Phase 0.  
   - `--no-llm` → exit with clear error (tester requires Gemini).

**Post-implementation manual check (any eligible work_dir):** run `run_tester` (or skip-phase0 + `--with-tester` only) against **one** existing export that has `rules_extracted.json` + processed NL. Expect: (re)creates `linearized_model_for_cross_critic.txt`, writes `tester_report.json`, no re-extract. Prefer a work_dir **without** a prior linearization file to prove generation; optionally repeat on a work_dir that already has one to prove idempotent overwrite.

---

## Relationship to other stages (normative)

| Stage | Primary question | Inputs |
|--------|------------------|--------|
| **Precheck** | Pathway refs + coarse numeric heuristics | NL file + `MetaScheme` |
| **varprod trigger validate** | Product factors guarded in trigger (deterministic) | `rules[]` IR |
| **Tester (this plan)** | **Does each NL line’s obligation match the corresponding rule’s formal body?** | Processed NL + **full linearization** |
| **Pivot critic** | NL ↔ **structural** synthetic summary + varprod excerpt | Effective NL + `synthetic_en.md` |
| **Cross-critic** | **Cross-rule** encoding coherence | Processed NL + linearization |
| **Template suite (Z3)** | Executable worlds vs goldens | `meta_scheme` + template JSON |

**Tester vs cross-critic (critical):**

- **Tester:** line-aligned audit — NL line *i* ↔ rule *R000i* (by order and/or explicit `nl_pointer` / `formal_pointer`). Focus: wrong threshold, wrong operator, missing trigger factor, wrong template class for the English shape, PREEMPTION target mismatch **for that line**, SET membership wrong, etc.
- **Cross-critic:** patterns **spanning** multiple rules — same denial idea split across variables, duplicated obligation shapes with inconsistent slots, etc. **Do not** duplicate cross-critic’s mandate in the tester prompt; cross-reference in findings only when a single-line fix would break cross-rule coherence.

**Tester vs pivot critic:**

- Pivot critic keeps **synthetic_en** + pathway/preemption **skeleton** checks.
- Tester owns **readable formal content** via linearization.

---

## Data sources (per run)

### Processed NL

Use the **same resolution as today** for `nl_text_for_artifacts` in `run.py`:

- Start from `nl_for_precheck` text (post–extract rewrites when written to `nl_after_extract_rewrites.txt`).
- Persisted as `rules_source.txt` in `work_dir`.

**Prompt label:** “Processed NL (one statement per line; line order matches extract order).”

Optional enhancement (v1.1): prepend **1-based line numbers** in the prompt payload only (do not mutate the file), e.g. `01. …`, matching `linearized_nl_and_model.txt` style — helps the model align `R0003` ↔ “line 3”.

### Linearized model

Reuse **`pivot_pipeline/linearize_rules.py`** → `linearize_rules_for_cross_critic(rules)`.

**Orchestration change:** Write **`work_dir/linearized_model_for_cross_critic.txt`** (keep filename for backward compatibility) **whenever** `--with-tester` **or** `--with-cross-critic` runs — **after** `rules_extracted.json` is final for that stage (post structural repair, before tester). Today linearization is only built inside the cross-critic block; move generation to a shared helper call earlier.

Also set `summary["linearized_model_for_cross_critic"]` when tester runs alone.

**Remove from tester prompt:** `<<<SYNTHETIC_EN>>>` and `<<<Z3_SUMMARY>>>` (Z3 optional one-line note in prompt header only: “Tester does not use Z3; behavior checks are template-suite.”).

---

## Prompt design (`prompts/tester_pivot_semantic.md`)

Replace body with a **rule-content alignment** contract. Suggested sections:

### 1. Role

You audit **semantic alignment between processed natural-language policy lines and the linearized Pivot IR** — one NL line should correspond to one rule id (`R0001`, …) in **extract order**.

Verdict **`ok`** only if every NL line is **faithfully encoded** in its rule’s linearized form (allowing benign paraphrase where **logic, thresholds, scope, and variables** are preserved).

### 2. How to read linearized rules (normative legend)

Include a **fixed interpretation block** (not policy-specific) explaining each template pattern:

| Pattern | Meaning for the model |
|---------|------------------------|
| `R0001 \| CONSTANT_RELATIONAL \| var OP value \| yields SATISFIED` | Unconditional (or global) comparison; `yields SATISFIED` means satisfying the comparison is the rule’s positive outcome. |
| `R0005 \| VARIABLE_RELATIONAL \| left OP right \| yields …` | Two variables compared. |
| `R0007 \| SET_INCLUSION \| var IN […] \| yields …` / `NOT_IN` | Finite enumeration membership. |
| `R0003 \| LOGICAL_IMPLICATION \| IF (…) THEN (…)` | Conditional: antecedent must hold for consequent to apply. Nested `AND` / `OR` / `NOT` in parentheses. |
| `(a * b) LTE n` in THEN | Variable×variable product bound (`varprod_cmp`); **both** factors should appear in NL when NL describes a product. |
| `R0017 \| PREEMPTION \| IF … THEN BYPASS_RULE target R0001` | When condition holds, rule `R0001` is bypassed (not evaluated on pathway). |
| `R0018 \| EXCLUSIVE_CHOICE \| mode=… variables=[…]` | Exactly one / at most one of listed vars. |
| `R00xx \| ARITHMETIC_EVALUATION \| …` | Single arithmetic step then compare to limit. |
| `R00xx \| LOGICAL_IFF \| IFF … <=> …` | Biconditional. |

**Operators:** `EQ`, `NEQ`, `GT`, `LT`, `GTE`, `LTE` — standard numeric/boolean comparisons on named policy variables.

**Variable names:** snake_case identifiers from the registry/extract phase; string literals in quotes or bare tokens for enum-like values (`WRITE`, `EXTERNAL`, `true`).

**Order convention:** Rule `R000k` is expected to encode **NL line k** (1-based). Flag **`misalignment`** if line count ≠ rule count or if a line clearly maps to a different `rule_id`.

**Benign differences (do NOT flag):**

- Wording paraphrase with same logic.
- Extra defensive guards in formalization (e.g. `GTE 0` on factors) **unless** they change meaning vs NL.
- PREEMPTION omission from pathway lists (pathway design); tester checks **PREEMPTION lines themselves** against NL bypass language.

**Do flag:**

- Wrong numeric threshold, wrong operator (`LT` vs `LTE`).
- Wrong variable or enum token.
- NL product/limit split across trigger vs consequent incorrectly vs NL intent.
- Missing NL obligation (no rule) or extra rule with no NL line.
- Template class clearly wrong for English shape (e.g. unconditional NL encoded as unrelated implication).
- PREEMPTION target or action does not match NL bypass scope.

### 3. Output JSON (strict)

Keep **`TesterReport`** shape; extend categories:

```text
verdict: "ok" | "issues"
findings[]:
  id, severity (info|warn|critical)
  category:
    omission | contradiction | threshold | wrong_operator | wrong_variable
    | template_mismatch | preemption_mismatch | ordering | misalignment | other
  nl_pointer: quote or "line N: …"
  formal_pointer: "R000n" (+ optional linearized fragment)
  explanation, recommendation
notes: optional
compared_against: "processed_nl_and_linearized_model"  # new field on report (optional v1)
```

Require **`compared_against`** constant in JSON for traceability (mirror cross-critic).

### 4. Placeholders

```text
<<<PROCESSED_NL>>>
<<<LINEARIZED_MODEL>>>
```

Truncate each at ~14k chars (same as today); linearization is usually smaller than NL for typical policies.

---

## Code changes

### A. `post_model_workflow.py`

- Change `run_pivot_tester(*, processed_nl: str, linearized_model: str, …)` — drop `synthetic_en` / `z3_summary` from required args.
- Extend `TesterFinding.category` Literal with new categories (backward compatible: map unknown LLM categories to `"other"` in parse if needed, or strict validate).
- Add optional `compared_against: str = "processed_nl_and_linearized_model"` on `TesterReport`.
- Update `format_tester_report_terminal` header: **“Pivot Tester (NL ↔ linearized IR)”**.
- Keep `tester_handoff_from_report` — add `compared_against` when present.

### B. `run.py`

Extract shared helper (used by full pipeline **and** replay CLI):

```python
def build_and_write_linearized(*, work_dir: Path, rules: list[dict]) -> str:
    linearized = linearize_rules_for_cross_critic(rules)
    lin_path = work_dir / "linearized_model_for_cross_critic.txt"
    lin_path.write_text(linearized, encoding="utf-8")
    return linearized
```

**Ordering invariant:** in `run_pivot_pipeline`, the block order after precheck must remain:

```text
build_and_write_linearized  (if with_tester or with_cross_critic)
→ if with_tester: run_pivot_tester → tester_report.json
→ if not skip_critic: semantic critic loop
→ if with_cross_critic: …
```

Never run pivot critic before tester when `--with-tester` is set.

1. After precheck (and varprod refresh), **before** tester block — call `build_and_write_linearized` when `with_tester or with_cross_critic`.

2. Replace tester call:

   ```python
   run_pivot_tester(processed_nl=nl_text_for_artifacts, linearized_model=linearized)
   ```

3. Cross-critic block: **reuse** `linearized` if already built; else build once.

4. **`--skip-phase0` + `--with-tester` without `--with-critic`:** load `rules_json`, compile, precheck, linearize, tester, write summary with outcome `ok` / `blocked_tester` — **do not** require critic gate. Ensure early-return paths do not skip tester when flag is set.

5. `run_summary.json`: add `tester_compared_against: "processed_nl_and_linearized_model"` and `tester_report` path when tester runs.

### C. `cli.py`

- Update `--with-tester` help: *“Per-rule processed NL vs linearized IR (`tester_report.json`); after precheck, **before** `--with-critic`.”*
- Document generic replay example in `--help` epilog or README (`--work-dir`, `--skip-phase0`, `--with-tester`).

### C2. `run_tester.py` (new thin entry)

- Same spirit as `cross_coherence.py`: `--work-dir`, `--input`, optional `--rules-json`, `--fail-on-tester-findings`, `--repo-root`.
- Internally: `run_pivot_pipeline(..., skip_phase0=True, with_tester=True, skip_critic=True, with_cross_critic=False, …)` **or** call extracted `run_tester_segment(work_dir, …)` to avoid duplicating compile logic.
- Register optional console script in `pyproject.toml`: `pivot-tester = pivot_pipeline.run_tester:main` (optional but recommended for PML ergonomics).

### D. Tests

| Test | Intent |
|------|--------|
| `test_run_pivot_tester_prompt_includes_linearization` | Mock LLM; assert placeholders filled. |
| `test_tester_report_parses_new_categories` | Pydantic accepts extended categories. |
| `test_run.py_writes_linearized_before_tester` | Flag `--with-tester` only → artifact exists. |
| `test_skip_phase0_with_tester_only` | Replay path: no critic invoked; `tester_report.json` written. |
| `test_run_tester_cli_replay_fixture` | Mock LLM; minimal temp work_dir with `rules_extracted.json` + `rules_source.txt`. |
| Golden prompt snippet | Snapshot optional: legend section present. |

### E. Documentation

- **`ARCHITECTURE.md`**: Tester box → “NL ↔ linearized IR (per-rule content)”.
- **`dev_plan_pivot_repairer_tester_post_model_v1.md`**: Add status note pointing here; mark old tester description superseded.
- **`pivot_pipeline/README.md`**: One line on `--with-tester` new role.

---

## Orchestration diagram (updated)

```text
extract → compile → Z3 → synthetic_en → precheck
    → [build linearized_model.txt]
    → [--with-tester: NL ↔ linearized audit]
    → [--with-critic: NL ↔ synthetic + varprod excerpt]
    → [--with-cross-critic: NL ↔ linearized cross-rule coherence]
    → …
```

**Default recommendation for thorough runs:**

```text
pivot-pipeline --input … --work-dir … --with-tester --with-critic --with-cross-critic …
```

---

## Non-goals (v1)

- **Tester → Repairer_Piv interactive loop** (use handoff JSON manually or follow-up dev plan).
- **Automatic re-extract** of single lines from tester findings.
- **Replacing pivot critic or cross-critic** — all three remain distinct.
- **Changing linearization format** (reuse cross-critic output verbatim).
- **Using `meta_scheme.json` directly in the prompt** — linearization is the human-facing view; meta_scheme stays for compile/Z3.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| LLM flags benign paraphrase | Strong “benign differences” section; prefer `warn` over `critical` for wording-only. |
| Line count ≠ rule count after extract edits | Explicit `ordering` / `misalignment` category; precheck could add deterministic count check (optional fast path). |
| Token limits on large policies | Truncate with marker; future: chunk by rule ranges. |
| Overlap with cross-critic findings | Prompt NON-goals: “do not report cross-rule outcome-split patterns — cross-critic owns those.” |
| False confidence on partial linearization | Legend must state linearization is **complete** formal content for each rule, not a summary. |

---

## Follow-ups (v2+)

1. **Tester → Repairer semantic** gate (mirror critic `REPAIR` / `PROCEED_INCOMPLETE`).
2. Deterministic **pre-tester** checks: rule count vs NL line count; every `R000n` referenced in linearization exists in NL order.
3. Rename artifact to `linearized_model.txt` with symlink/compat note for cross-critic paths.
4. Numbered NL in prompt builder helper shared with cross-critic docs.
5. CI golden: `Test_input2` tester must PASS on known-good export.

---

## Done criteria (v1)

- [x] `tester_pivot_semantic.md` rewritten with linearization legend + new placeholders.
- [x] `run_pivot_tester` takes processed NL + linearized model only.
- [x] `run.py` builds/writes linearization before tester; **tester always before pivot critic** when both enabled.
- [x] **`--skip-phase0` + `--with-tester`** replays tester on existing work_dir without critic.
- [x] **`run_tester.py`** / **`pivot-tester`** entry for generic replay.
- [x] `TesterReport` categories extended; `compared_against` field set.
- [x] CLI help + ARCHITECTURE updated.
- [x] Unit tests green.
- [x] Old synthetic-based tester behavior removed.

---

## Appendix: optional local smoke paths (not part of v1 requirements)

These are **illustrative** exports in this workspace; implementation must not hard-code or depend on them.

| Illustrative export | Notes |
|---------------------|--------|
| Any `work_dir` with `rules_extracted.json` + `rules_source.txt` | Generic replay target |
| `NagV/exports/pivot_runs_test_input2/` | NL + linearization already paired (`linearized_nl_and_model.txt`) |
| `NagV/exports/pivot_runs/scope_rewriter_2_wfm/` | Large policy, completed e2e |
| `NagV/exports/pivot_runs/policy_spec_wfm/` | Example where linearization was never saved (tests regen path) |

Linearization module: `NagV/pivot_pipeline/linearize_rules.py` (`linearize_rules_for_cross_critic`).
