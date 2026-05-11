# Dev plan: NagV pipeline (WFM SMT profile → Nagini Python)

## 1. Purpose

**NagV** produces **Nagini-checkable Python** (or a **defined rejection**) from a **natural-language ruleset that has already been processed by WFM** using the **same workflow as the SMT pipeline** (`wfm_profile="smt"`, `smt/wfm/` prompts). The pipeline is **housed under `NagV/`** and is invocable as a single flow from NL file → WFM artifacts → LLM formalizer/critic rounds → **Nagini verification**.

## 2. Inputs and upstream contract (WFM)

### 2.1 What “same outputs as SMT WFM” means

Reuse the **existing chunked NL → WFM → handoff** contract from:

- `wfm_orchestration.nl_chunk_smt_policy_pipeline`

So for a given `--nl-file` (one rule per non-empty line, same as SMT):

- **`nl_chunk_progress.json`** (or equivalent progress schema for SMT) with resume / `pending_*` semantics
- **`wfm_handoffs/*.json`** — `HandoffBundle`-shaped JSON per chunk (same schema the SMT path consumes)
- Optional **manifest / export** patterns already used under `exports/nl_chunk_smt_runs/<stem>/` (work dir is configurable)

**NagV does not require the SMT formalizer or `policy_model.smt2`** for its core story; it only requires that **WFM has been run to completion** (or NagV runs WFM as phase 1 of the same CLI).

### 2.2 Handoffs NagV actually needs

From each handoff, NagV consumes at minimum:

- **`user_original_input`** and/or chunked narrative context (for critic alignment)
- **`lines[]`** with **`statement_nl`**, **`agent3_verdict`**, and any scope metadata needed to **drop or mark** `OUT_OF_SCOPE` lines

**Formalizer input assembly (implementation decision):**

- **Default:** concatenate **only `PASS`** lines’ `statement_nl` in `line_index` order, with clear separators and optional one-line headers citing `line_index` for traceability.
- **Alternative (config flag):** pass **structured JSON** (list of `{line_index, verdict, statement_nl}`) into the formalizer prompt so the model can skip or comment non-`PASS` lines explicitly. Choose one as default in code; document in `NagV/README` when added.

### 2.3 “Entire ruleset processed by WFM, not a bundle of one”

- **Phase A (WFM):** run **all chunks** until progress says complete (same as `nl_chunk_smt_policy_pipeline`), producing **multiple handoff files** or resuming from existing work dir.
- **Phase B (NagV core):** **aggregate** all PASS NL into **one formalization unit** (single module or single file) unless prompts require splitting (default: **one `output.py`** per run).

## 3. LLM agents and loops (budget = 4 each, independent)

All **Gemini** calls participating in NagV SHALL use **`ThinkingLevel.HIGH`** by default via the **NagV process bootstrap** (`NagV/nagv/runtime_env.py`: set `GEMINI_THINKING_LEVEL=high` unless `NAGV_GEMINI_THINKING_LEVEL=inherit` to reuse repo-wide setting). This applies to **WFM** (when launched from NagV), **formalizer**, and **critic** because they share `registry_stage.llm.gemini_call` / WFM `e2e_context`.

### 3.1 Formalizer

- **Prompt file:** `NagV/prompts/formalizer.md` (user-supplied content; repo holds path + placeholder until provided).
- **Behavior:** Emit **Python** intended to be **verifiable in Nagini** (`nagini_contracts`, contracts as appropriate). If the rules or a line is **outside Nagini-encodable scope**, the formalizer MUST **not** invent unsound code — return a **structured “refusal / out_of_scope”** artifact (exact schema TBD in prompt; implementation validates with Pydantic or JSON schema).
- **On success:** body is **full module text** (or extract from fenced block).

### 3.2 Syntax gate

- **`ast.parse`** or **`compile()`** on the emitted module text.
- Failure → **Nagini-syntax-repair loop** (below), not critic (optional: still run critic after syntax OK; **per user: any formalizer output must eventually pass critic + Nagini**).

### 3.3 Critic

- **Prompt file:** `NagV/prompts/critic.md`.
- **Inputs:** aggregated NL (and/or structured line list), current Python candidate, optional prior critic notes.
- **Outputs (structured):** `aligned: bool`, `drifts: [...]` with **provenance** (which NL phrase vs which code region), **`suggested_fixes`** that **do not** introduce unstated policy; allow **reasonable implicatures** per prompt.
- **Loop L1 — Formalizer ⟷ Critic:** max **4** full rounds: formalizer produces/updates → syntax check → critic. **Stop early** if critic reports `aligned` and syntax OK. If budget exhausted → **reject** with reason `critic_budget_exhausted` or `semantic_misalignment_unresolved`.

**Independence:** L1 counter is **not** nested inside other loops; it is its own cap of 4.

### 3.4 Nagini phase

Assume **Nagini** installed in **`NagV/.venv`** (existing convention) or path from `NAGV_NAGINI_PYTHON` / `NAGV_NAGINI_EXE`.

1. **Subprocess:** `nagini output.py` (plus flags `-v` for logs in artifact).
2. **Compile / Nagini front-end errors** (Python errors, Nagini parse errors): extract stderr; **Loop L2 — formalizer compile repair:** max **4** rounds. Each round: feed error text + current code + NL context → formalizer → **must pass critic** before returning to **Nagini** (per user: formalizer changes are always revalidated by critic, then Nagini).

3. **Verification failures** (counterexamples, failed `Ensures`): extract Viper/Nagini messages; **Loop L3 — formalizer proof repair:** max **4** rounds. Same discipline: formalizer → critic → Nagini.

**Independence:** L2 and L3 each have their own counter (4+4); **reset policy:** optional design choice — **recommend:** start L3 at 0 after first full verification attempt; do **not** decrement L1 when entering L2/L3 (user asked no containment: interpret as **separate budgets**, not shared pool).

### 3.5 End states (defined outcomes)

| Outcome | Meaning |
|--------|--------|
| `success` | Python file written; Nagini **Verification successful** |
| `rejected_out_of_scope` | Formalizer (or critic) concluded policy not formalizable in Nagini fragment |
| `rejected_critic_budget` | L1 exhausted |
| `rejected_nagini_syntax_budget` | L2 exhausted |
| `rejected_nagini_verify_budget` | L3 exhausted |
| `error_api` | Gemini / network / rate limit |
| `error_nagini_missing_env` | Java / venv / Nagini not runnable |
| `error_timeout` | User-defined wall-clock or per-call timeout |

## 4. Artifacts and observability

Under work dir (e.g. `exports/nagv_runs/<stem>/`):

- `nagv_progress.json` — phase, last handoff id, loop counts L1/L2/L3, last error class
- `wfm_handoffs/` — symlink or copy from SMT work dir if NagV orchestrates WFM
- `candidates/` — `round_XXX_formalizer.py`, critic JSON responses
- `final.py` or `policy_nagini.py` — successful output
- `verification_log.txt` — full Nagini stdout/stderr
- `run_summary.json` — outcome enum, durations, token usage if available

## 5. Implementation layout (repo)

```
NagV/
  nagv/
    __init__.py
    runtime_env.py          # GEMINI_THINKING_LEVEL for NagV runs
    pipeline.py             # orchestration (phases + loops)
    wfm_phase.py            # call into nl_chunk_smt_policy_pipeline or import its helpers
    formalizer.py           # prompt load + gemini_complete + parse
    critic.py
    syntax_check.py
    nagini_runner.py        # subprocess + error classification
    models.py               # Pydantic for LLM JSON contracts
    cli.py                  # python -m nagv.cli ...
  prompts/
    formalizer.md           # (from user)
    critic.md               # (from user)
```

**Packaging:** add optional `[nagv]` extra in root `pyproject.toml` if needed (`google-genai` already pulled via registry); document `NagV/.venv` for Nagini binary.

## 6. Decisions locked for v1

1. **WFM:** Reuse **`nl_chunk_smt_policy_pipeline`** (SMT profile only for WFM prompts); NagV CLI **`--wfm-work-dir`** can point at existing SMT run to **skip WFM** when handoffs already exist.
2. **Thinking:** **`NAGV_GEMINI_THINKING_LEVEL` default `high`**; `inherit` leaves `GEMINI_THINKING_LEVEL` untouched. Implemented: `NagV/nagv/runtime_env.py` (`apply_nagv_gemini_defaults()`); NagV CLI must call it at startup **before** any WFM or `gemini_complete` import path runs.
3. **Budgets:** L1=L2=L3=**4**, independent counters.
4. **Discipline after formalizer edit:** always **critic** (if not raw syntax-only micro-fix policy — **user required critic + Nagini**; v1 always full critic pass before Nagini).
5. **Nagini scope refusal:** formalizer emits explicit **OOS JSON**; pipeline surfaces as `rejected_out_of_scope`.

## 7. Follow-up after user drops prompt files

1. Drop **`formalizer.md`** / **`critic.md`** into `NagV/prompts/`.
2. Tighten **`models.py`** JSON shapes to match prompt I/O exactly.
3. Add **pytest** with **mocked `gemini_complete`** and **mocked `nagini`** subprocess for golden-path and budget-exhaustion tests.

## 8. Done criteria

- One command runs **NL file → WFM (SMT) → NagV → `success` or defined `rejected_*` / `error_*`**.
- **Gemini HIGH** thinking for all NagV-invoked WFM + NagV LLM calls (default).
- Logs sufficient to **audit** each loop and final Nagini output.
