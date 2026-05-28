# Dev plan: Pivot Tester — JSON / schema repair retry (extract-style)

**Status:** Implemented  
**Priority:** P1 (recruitment `blocked_tester` with parse error, no `tester_report.json`)  
**Symptom:** `tester failed: Unterminated string starting at: line 36 column 21 (char 2237)` — repeatable on retry  
**Related run:** `NagV/exports/pivot_runs/recruitment_16_temp_wfm` — `pivot_pipeline.run_tester` with `--interactive-tester`  
**Pattern to mirror:** `extract_one_line_with_repairs` + `prompts/extract_schema_repair.md` + `PIVOT_EXTRACT_SCHEMA_REPAIR_MAX`

---

## 1. Problem (simple terms)

**Pivot Tester** asks Gemini for one JSON object (`verdict`, `findings`, …). The model often embeds **raw double quotes** inside `nl_pointer`, `explanation`, or `recommendation` (e.g. quoting NL fragments like `"Salesforce Service Cloud"`) **without** JSON escaping → `json.loads` fails with **Unterminated string**.

Today `run_pivot_tester()` in `post_model_workflow.py` does:

```text
raw = llm(prompt)
data = parse_json_object(raw)
report = TesterReport.model_validate(data)
```

Any parse or Pydantic error **bubbles to** `run.py` / `run_tester.py` as a generic exception → **`outcome: blocked_tester`**, **`message: tester failed: …`**. No `tester_report.json`, no triage, no distinction from “tester found real policy issues.”

Re-running the same command is **non-deterministic** (same failure class on consecutive runs).

This is **not** fixed by `--with-test-repair` (that is **Test-Repairer** on **approved findings** after a **valid** tester report).

---

## 2. Root cause (code)

| Location | Gap |
|----------|-----|
| `post_model_workflow.run_pivot_tester` | Single LLM call, no repair loop |
| `tester_interactive_loop` | Calls `run_pivot_tester` directly |
| `run.py` L560–567 | `except Exception` → `blocked_tester` for **any** tester failure |
| Extract / critic | Extract has repair loop; critic has **legacy fallback** on parse fail — tester has **neither** |

---

## 3. Goal

- After tester LLM returns invalid JSON or invalid `TesterReport` shape, run up to **N** **repair** LLM calls (same pattern as extract schema repair).
- On success: normal flow (`tester_report.json`, interactive triage if `issues`).
- On exhaustion: **`blocked_tester`** with explicit message: `invalid tester JSON after N repair attempts: …` and persist **last raw** + **repair trace** for debugging.
- Optional: split outcome label **`blocked_tester_output_parse`** vs **`blocked_tester`** (findings / `--fail-on-tester-findings`) — improves operator clarity.

---

## 4. Proposed fix (mirror extract)

### P0 — `run_pivot_tester_with_repairs`

New function in `post_model_workflow.py` (or small `tester_parse.py` if preferred):

```text
run_pivot_tester_with_repairs(
    processed_nl, linearized_model, *,
    llm=..., max_repairs=None,
) -> tuple[str, TesterReport]
```

Loop (same structure as `extract_one_line_with_repairs`):

1. `raw = llm(main_prompt)` on first iteration; else `raw = llm(repair_prompt)`.
2. Try `_tester_report_from_raw(raw)`:
   - `parse_json_object(raw)`
   - `TesterReport.model_validate(data)`
   - default `compared_against` if missing (existing behavior)
3. On success → return `(raw, report)`.
4. On `json.JSONDecodeError`, `ValueError` (parse), or `pydantic.ValidationError` → build diagnostic, if `attempt < max_repairs` call repair LLM; else raise **`TesterOutputError`** (new typed exception) with diagnostic text.

**Env:** `PIVOT_TESTER_JSON_REPAIR_MAX` (default **3**, clamp 0–10) — parallel to `PIVOT_EXTRACT_SCHEMA_REPAIR_MAX`.

**Wire:** `tester_interactive_loop` calls `run_pivot_tester_with_repairs` instead of `run_pivot_tester`. Keep `run_pivot_tester` as thin wrapper or deprecate in favor of `_with_repairs` only.

### P1 — Repair prompt `prompts/tester_json_repair.md`

Template placeholders (mirror extract repair):

| Placeholder | Content |
|-------------|---------|
| `<<<INVALID_OUTPUT>>>` | Trimmed bad raw (cap ~6000 chars) |
| `<<<DIAGNOSTIC>>>` | Machine text: parse error line/col, or Pydantic field bullets |
| `<<<EXPECTED_SCHEMA>>>` | Short excerpt: `verdict`, `findings[]` fields, `compared_against`, enums — from `tester_pivot_semantic.md` “Output (strict)” |

**Repair rules (strict):**

1. Output **only** one JSON object; no markdown fences, no prose.
2. **Preserve** audit intent from invalid output where readable; do **not** invent new policy findings.
3. **Escape** all string values: use `\"` inside JSON strings; no raw `"` inside unescaped spans.
4. If invalid output is empty or unrecoverable, emit minimal valid JSON: `{"verdict":"issues","compared_against":"processed_nl_and_linearized_model","findings":[],"notes":"repaired from unparseable output"}` only when clearly no findings were present; otherwise reconstruct findings from fragments.
5. `verdict` ∈ `ok` | `issues`; finding `severity` / `category` enums exactly as main tester prompt.

Do **not** pass full NL + linearized model into repair prompt (keeps tokens down); schema + invalid blob + diagnostic suffice for JSON fixes.

### P2 — Diagnostics helper

`build_tester_repair_context(raw, exc) -> TesterRepairContext` with:

- `stage`: `json` | `schema`
- `invalid_raw_trimmed`
- `messages`: human-readable list (reuse `_pydantic_error_lines` pattern from `extract.py` or shared util)

`format_tester_repair_diagnostic(ctx) -> str` for `<<<DIAGNOSTIC>>>`.

### P3 — Artifacts on failure / retry

| Artifact | When |
|----------|------|
| `tester_result.txt` | **Every** successful parse (final raw) — already planned in loop |
| `tester_result_invalid_attempt_{k}.txt` | Optional: each failed raw before repair (debug) |
| `tester_json_repair_trace.jsonl` | One line per repair attempt: `{attempt, stage, error_summary}` |

On **success after repair**, set `summary["tester_json_repair_attempts"] = k` (0 = first shot ok).

### P4 — `run.py` exception handling

- Catch **`TesterOutputError`** explicitly → `blocked_tester` (or `blocked_tester_output_parse`) + message includes repair exhaustion.
- Still catch unexpected exceptions separately (`tester failed: {e}`).
- **Do not** conflate with `fail_on_tester_findings` path.

### P5 — Tests (`tests/test_post_model_workflow.py` or new `test_tester_json_repair.py`)

| Test | Behavior |
|------|----------|
| `test_tester_repair_second_llm_fixes_json` | First LLM returns broken JSON; second returns valid minimal `ok` report |
| `test_tester_repair_fixes_pydantic` | Valid JSON but wrong enum → repair → valid |
| `test_tester_repair_exhausted_raises` | `max_repairs=0` + bad JSON → `TesterOutputError` |
| `test_run_tester_interactive_loop_writes_report_after_repair` | Monkeypatch LLM sequence; `tester_report.json` exists |

### P6 — Docs

- `README.md` / `ARCHITECTURE.md` Step 5 Tester: mention `PIVOT_TESTER_JSON_REPAIR_MAX`.
- `run_tester.py` `--help` one line.

---

## 5. Non-goals (v1)

- Repair loop for **cross-critic** or **pivot critic** JSON (separate plans; critic has legacy verdict fallback only).
- Changing `TesterReport` schema or relaxing `extra="forbid"`.
- Sanitizing/truncating finding strings in code instead of LLM repair (optional P7 follow-up: strip unescaped quotes heuristically **before** repair as attempt 0 — not required if repair works).
- Interactive gate when repair exhausted (operator must re-run or lower max findings manually).

---

## 6. Files to touch

| File | Change |
|------|--------|
| `NagV/pivot_pipeline/post_model_workflow.py` | `run_pivot_tester_with_repairs`, `TesterOutputError`, env helper |
| `NagV/pivot_pipeline/prompts/tester_json_repair.md` | New repair prompt |
| `NagV/pivot_pipeline/tester_interactive_loop.py` | Call `_with_repairs` |
| `NagV/pivot_pipeline/run.py` | Typed exception, optional outcome split, summary fields |
| `NagV/pivot_pipeline/run_tester.py` | Document env var |
| `NagV/pivot_pipeline/tests/test_post_model_workflow.py` | Repair tests |

---

## 7. Acceptance (manual)

Re-run recruitment tester:

```powershell
.\.venv\Scripts\python.exe -m pivot_pipeline.run_tester `
  --work-dir NagV\exports\pivot_runs\recruitment_16_temp_wfm `
  --input NagV\exports\scope_rewriter\recruitment_16_temp_run\scope_rewriter\latest.nl `
  --with-test-repair `
  --interactive-tester
```

**Pass:** Either `tester_report.json` written and terminal shows Tester verdict (ok or issues + triage), **or** clear message `invalid tester JSON after 3 repair attempts` with `tester_json_repair_trace.jsonl` present.

**Fail v1:** Same `Unterminated string` on first shot with **no** repair attempts logged.

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Repair LLM also returns bad JSON | Bounded retries; save last raw |
| Repair “fixes” JSON but drops findings | Prompt: preserve intent; compare finding count in tests |
| Extra latency/cost per run | Default max 3; env tunable to 0 for dev |
| Duplicate logic vs extract | Shared `_trim_for_prompt` / pydantic bullet helper in `json_repair_util.py` (optional small refactor) |

---

## 9. Summary

**Same issue on retry:** yes — **technical JSON parse failure**, not policy findings.

**Fix:** Add **extract-style** repair loop around `run_pivot_tester` so malformed tester responses get **automatic JSON/schema repair attempts** before `blocked_tester`.
