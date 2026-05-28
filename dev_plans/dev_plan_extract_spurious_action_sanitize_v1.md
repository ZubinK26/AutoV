# Dev plan: Extract — strip spurious `action` (and other template-leak keys) before validation

**Status:** Implemented  
**Priority:** P1 (blocks recruitment `blocked_extraction_validation` on `--skip-phase0`)  
**Symptom:** `line N: schema: action: Extra inputs are not permitted` on non-`PREEMPTION` lines (e.g. reporting-tool OR, support-queue OR)  
**Related run:** `NagV/exports/pivot_runs/recruitment_16_temp_wfm` — extract after Phase 0 complete  

---

## 1. Problem (simple terms)

Phase 1 **extract** asks Gemini for one JSON rule per line of `phase0_normalized_nl.txt`.

The Pivot IR schema is strict (`extra="forbid"` on Pydantic models). Only **`PREEMPTION`** rules may have top-level **`action`** (and usually **`target_rule_id`**).

The extract model sometimes copies **`action`** onto **`LOGICAL_IMPLICATION`**, **`SET_INCLUSION`**, **`K_OF_N`**, etc. — often on lines about escalation, rejection, or “must not” that *sound* like preemption in English.

- Automatic **schema repair** (up to `PIVOT_EXTRACT_SCHEMA_REPAIR_MAX` attempts) often **does not** remove the stray key.
- **`--interactive-policy`** only loops on **`ExtractAbort`**, not on **`ExtractValidationError`** — the run exits with `blocked_extraction_validation` and no TTY recovery.
- Re-running extract is **non-deterministic** (fails on line 17, then 19, etc.).

This is **not** fixed by editing specific NL lines: the English is fine; the **JSON shape** is wrong.

---

## 2. Root cause (code)

`sanitize_rules_jsonable()` in `NagV/pivot_pipeline/ir.py` already drops unknown top-level keys per `template_class` (see `test_ir_rule_sanitize.py` — strips `notes`, nested junk, etc.).

**Extract does not use it today.** `validate_rule_dict()` in `NagV/pivot_pipeline/extract.py` calls `cls.model_validate(rule)` on the **raw** LLM dict, so illegal keys fail before sanitization runs.

Sanitization **is** applied later at `load_rules_and_compile()` — too late for Phase 1 batch extract.

---

## 3. Goal

- Extract accepts valid semantics even when the model adds **forbidden top-level keys** for the chosen `template_class`.
- **`action`** / **`target_rule_id`** stripped unless `template_class == "PREEMPTION"`.
- All other template-specific leaks stripped via existing allowlist logic (no duplicate implementation).
- Optional: one-line log when keys are dropped (debug / `extract_rewrite_log.jsonl`).
- No change to NL policy text required for this bug class.

---

## 4. Proposed fix (minimal, preferred)

### P0 — Wire sanitize into extract validation

In `validate_rule_dict()` (or `_rule_from_raw_output()` immediately after `parse_json_object`):

```python
from pivot_pipeline.ir import sanitize_rules_jsonable

rule = sanitize_rules_jsonable([rule])[0]
# then model_validate as today
```

Or export a thin helper `sanitize_rule_dict(rule: dict) -> dict` wrapping `_sanitize_rule_dict` for clarity.

**Acceptance:** Given input:

```json
{
  "template_class": "LOGICAL_IMPLICATION",
  "rule_id": "R0017",
  "applies_to": "GLOBAL",
  "action": "BYPASS_RULE",
  "trigger_condition": { ... },
  "required_condition": { ... }
}
```

`validate_rule_dict` succeeds and returned dict has **no** `action`.

### P1 — Prompt hardening (belt and suspenders)

In `NagV/pivot_pipeline/prompts/extractor.md`, add a short **FORBIDDEN KEYS** block:

- Do **not** emit `action` or `target_rule_id` unless `template_class` is exactly `PREEMPTION`.
- Escalation / “must not advance” / “until” lines → `LOGICAL_IMPLICATION` (or vNext / temporal addendum), **not** `PREEMPTION`, unless the NL is explicitly a bypass of another rule id.

Mirror one sentence in `prompts/extract_schema_repair.md` (remove stray `action` when template is not `PREEMPTION`).

### P2 — Optional observability

When sanitize drops top-level keys, append to `work_dir/extract_sanitize_log.jsonl`:

```json
{"line_index": 19, "template_class": "LOGICAL_IMPLICATION", "dropped_keys": ["action"]}
```

Gate behind env `PIVOT_EXTRACT_LOG_SANITIZE=1` (default off or on — product choice).

### P3 — Optional UX (out of scope for P0)

Interactive gate on `ExtractValidationError` (like ABORT rewrite) — separate plan if still needed after P0.

---

## 5. Non-goals

- Changing WFM or `phase0_normalized_nl.txt` for this issue.
- Relaxing Pydantic `extra="forbid"` globally (keeps compile-time safety).
- Auto-converting mistaken `PREEMPTION` to `LOGICAL_IMPLICATION` when `action` is present (sanitize-only; if both `PREEMPTION` and invalid `target_rule_id`, existing cross-rule validation still applies).

---

## 6. Files to touch

| File | Change |
|------|--------|
| `NagV/pivot_pipeline/extract.py` | Call sanitize before `model_validate` in `validate_rule_dict` |
| `NagV/pivot_pipeline/ir.py` | Optional: `sanitize_rule_dict()` public wrapper |
| `NagV/pivot_pipeline/prompts/extractor.md` | FORBIDDEN KEYS note |
| `NagV/pivot_pipeline/prompts/extract_schema_repair.md` | Same note for repair pass |
| `NagV/pivot_pipeline/tests/test_extract.py` | Regression: spurious `action` on `LOGICAL_IMPLICATION` |
| `NagV/pivot_pipeline/tests/test_ir_rule_sanitize.py` | Regression: `action` stripped on non-PREEMPTION |

---

## 7. Test plan

1. **Unit:** `sanitize_rules_jsonable` / extract path — `LOGICAL_IMPLICATION` + `action: "BYPASS_RULE"` → validates; output has no `action`.
2. **Unit:** `PREEMPTION` + `action` + valid `target_rule_id` → unchanged (still validates with cross-rule checks).
3. **Unit:** `CONSTANT_RELATIONAL` + `notes` → still strips `notes` (existing behavior).
4. **Manual:** Re-run recruitment extract:

   ```powershell
   python -m pivot_pipeline `
     --input NagV\exports\scope_rewriter\recruitment_16_temp_run\scope_rewriter\latest.nl `
     --work-dir NagV\exports\pivot_runs\recruitment_16_temp_wfm `
     --interactive-policy `
     --skip-phase0
   ```

   Expect Phase 1 to complete (registry → compile → …) barring unrelated API 503s.

---

## 8. Rollout / operator note

After deploy, **no** `--reset-progress` needed for this fix — re-run `--skip-phase0` on the same work dir.

If extract had partially written `phase1_rules_raw.json` from an older attempt, delete it or let the run overwrite on success (today failed runs may not write it).

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Strip `action` on a line that was *meant* to be `PREEMPTION` but mis-tagged | Prompt P1; cross-rule checks if template is `PREEMPTION` without `target_rule_id` still fail loudly |
| Hiding model quality issues | Optional P2 log of dropped keys |
| Divergence extract vs compile sanitize | Same `_sanitize_rule_dict` code path |

---

## 10. Summary

**One-line fix:** Use the **existing** `sanitize_rules_jsonable` allowlist in **extract**, not only at compile. That removes spurious `action` (and other junk keys) before Pydantic validation so Phase 1 does not fail on random line numbers.
