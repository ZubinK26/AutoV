# Dev plan: NagV — Nagini translation gate before semantic critic

## 1. Purpose

Restructure the NagV **post-WFM** loop so that:

1. **Nagini-feasibility** (translation / contract frontend) is enforced **before** the **semantic** (LLM critic) loop.
2. **Semantic alignment** runs on candidates that **already translate** under Nagini’s frontend.
3. A **final Nagini verification** pass confirms proofs (and translation) still hold after semantic edits.
4. **Repair budgets** are explicit, with a **shared pool** for **Nagini-directed repair** across the first gate and the final verify, plus a **floor** so the final phase is not starved.

This document is the agreement distilled from design discussion; implementation follows these sections.

## 2. Current behavior (baseline)

Today (see `NagV/nagv/pipeline.py`):

- **L1:** formalizer → `ast.parse` → **critic** → repair inner loop (`INNER_FORMAL_CRITIC`) until critic PASS or exhausted; **L1_ROUNDS** outer rounds.
- **L2:** Nagini **frontend / translation** failures → `formalizer_repair_critic_align` with repair bootstrap (still runs **critic** inside that align).
- **L3:** Nagini **verification** failures → same align pattern.

**Problem addressed:** Critic cycles can run on code Nagini will never translate (e.g. illegal `@Requires`/`@Ensures` shapes), wasting budget and obscuring the real blocker.

## 3. Target pipeline (high level)

```text
WFM + NL aggregate (unchanged)
    ↓
[Phase A] Initial candidate: formalizer (and optional short inner loop only if needed — see §4.1)
    ↓
[Phase B] NAGINI_TRANSLATION_GATE — run Nagini in “fail-fast” translation/static mode (§4.2)
    ↓ repair until gate passes or NAGINI_REPAIR budget exhausted
[Phase C] SEMANTIC_GATE — critic PASS
    ↓ semantic repair until PASS or SEMANTIC_REPAIR exhausted
[Phase D] NAGINI_VERIFY_FINAL — full Nagini verification (§4.2)
    ↓ repair until success or remaining NAGINI_REPAIR exhausted
success / defined reject outcomes
```

**Ordering rule:** No **critic** run on a candidate until **Phase B** passes for that candidate line of development (new formalizer output or post–Phase-B repair only).

## 4. Definitions

### 4.1 Phase A — formalizer

- Keep **Python syntax** check (`ast.parse` / existing `syntax_errors`) **before** invoking Nagini in Phase B (cheap, local).
- **Remove** critic from the pre–Phase-B path: inner loop after formalizer is **repair-on-syntax-only** or **repair-on-Nagini-translation** feedback, not critic (exact loop structure in §6).
- Optional: single-shot formalizer then immediately Phase B; repairs in Phase B consume shared Nagini repair budget.

### 4.2 Nagini modes

Two **distinct** subprocess uses of Nagini (exact CLI flags / parsing reused from `nagv.nagini_runner` where possible):

| Mode | Intent | Success signal | Notes |
|------|--------|----------------|--------|
| **Translation gate** | Fail fast on frontend/type/contract shape errors | Process exit + NAGINI “translation” success heuristics already used for L2 class | Same class of errors as today’s L2 (`Translation failed`, etc.) |
| **Full verify** | Complete verification | Existing “Verification successful” (or current success detection) | Same as today’s L3 success path |

If a single Nagini invocation cannot be split cleanly, **document** that Phase B and D are the **same command** but Phase B treats **translation failure** as the gate and stops interpretation there; Phase D requires **full success**. Implementation choice: prefer **one** Nagini entrypoint with a parameter `gate: translation | full` that maps to timeout/flags/log parsing as appropriate.

### 4.3 Phase C — semantic (critic)

- Unchanged **verdict** contract: last `[VERDICT: PASS]` in critic output (`critic_passed`).
- Prompt expectation (§7): critic may assume candidate is **Nagini-translatable**; focus on **NL ↔ code** drift.

### 4.4 Repair agents

- **Nagini repair:** `repair_agent` / formalizer bootstrap driven by **Nagini stdout/stderr** (and optional syntax message), **no critic** in the loop body for Phase B/D.
- **Semantic repair:** same repair agent (or formalizer-with-feedback) driven by **critic** text, with prompt constraints **preserving Nagini-translatable contract style**.

## 5. Budgets (agreed refinement)

Avoid a single undifferentiated “shared” pool with no guardrails.

**Recommended:**

- **`NAGINI_REPAIR_CAP`** — single **pool** consumed by:
  - repairs after **translation gate** failures (Phase B), and
  - repairs after **final verification** failures (Phase D).
- **`NAGINI_REPAIR_FINAL_FLOOR`** — **minimum number of repair attempts** reserved for Phase D *until* Phase C has succeeded (i.e. pool can spend freely in B until `remaining <= floor`, then only D may spend below that threshold — exact state machine in §6). If `floor == 0`, behavior degrades to a simple shared cap.

**Semantic:**

- **`SEMANTIC_INNER_CAP`** — inner repair steps per critic round (analog to today’s `INNER_FORMAL_CRITIC`).
- **`SEMANTIC_ROUNDS`** — outer rounds if formalizer must rewrite from scratch after semantic exhaustion (analog to `L1_ROUNDS`); may be merged with inner depending on implementation.

**Independence (unchanged spirit):** semantic caps are **separate** from the Nagini pool; only the Nagini pool is **shared** between B and D with a floor.

Constants may replace or subsume today’s `INNER_FORMAL_CRITIC`, `L1_ROUNDS`, `L2_ROUNDS`, `L3_ROUNDS` with names above; migration table in §8.

## 6. Implementation plan (code)

### 6.1 `NagV/nagv/pipeline.py`

- Replace `formalizer_repair_critic_align` usage **before** first successful translation gate with a function e.g. `nagini_translation_align(formalizer → nagini_gate → repair_only)` that **never** calls `critique`.
- Introduce `semantic_align(critic → semantic_repair)` that **only** runs after translation gate PASS.
- Wire **final verify** after semantic PASS; on failure decrement **Nagini pool** (respecting floor rules).
- Map outcomes to `run_summary` / `nagv_progress.json`:
  - e.g. `rejected_nagini_translation_budget`, `rejected_semantic_budget`, `rejected_nagini_verify_budget`, or unified `rejected_nagini_repair_budget` with **detail** distinguishing B vs D (prefer explicit for debugging).
- Preserve CLI surface (`--skip-wfm`, `--work-dir`, etc.); extend progress JSON with new counters (`nagini_repair_used`, `semantic_round`, …).

### 6.2 `NagV/nagv/nagini_runner.py` (or adjacent)

- Expose **`run_nagini_gate`** vs **`run_nagini_verify`** (or single `run_nagini(..., mode=...)`).
- Ensure stderr/stdout classification distinguishes **translation** vs **verification** failure (reuse existing L2/L3 branching logic).

### 6.3 Prompts (`NagV/prompts/`)

| File | Change |
|------|--------|
| `formalizer.md` | Clarify **two-stage** goal: (1) Nagini-translatable contracts and structure; (2) NL fidelity — or defer “fidelity” emphasis to critic; avoid patterns Nagini rejects (e.g. lambdas in decorators unless truly supported). |
| `critic.md` | State **precondition:** code passed Nagini translation gate; focus audit on **semantic** alignment; flag contract edits that could break translation. |
| `repairer.md` | Two contexts (or sections): **NAGINI_DIAGNOSTIC** — fix translation/proof errors without broad rewrite; **CRITIC_FEEDBACK** — fix drift **without** breaking `@Requires`/`@Ensures` / Nagini idiom. |

Optional: **separate** `repairer_nagini.md` / `repairer_semantic.md` if one file becomes unwieldy; start with sections to minimize file sprawl.

### 6.4 Tests / fixtures

- Unit-test **budget floor**: mock Nagini to fail translation then succeed verify path; ensure final phase retains attempts.
- Golden-path test: translation fail → repair pass → critic pass → verify pass with **small** caps.

## 7. Non-goals (this iteration)

- Changing WFM or handoff aggregation (`wfm_phase.py`) beyond progress fields.
- Changing **Gemini model split** (Flash vs critic Pro) — already configured in `nagv/llm.py`.
- SMT pipeline or `registry_stage` defaults, except if `gemini_complete` needs a **no-op** hook for future per-phase hooks (not required for this plan).

## 8. Constant migration (from current `pipeline.py`)

| Current | New role (proposed) |
|---------|---------------------|
| `INNER_FORMAL_CRITIC` | Subsumed by `SEMANTIC_INNER_CAP` + possibly small syntax-only inner loop |
| `L1_ROUNDS` | `SEMANTIC_ROUNDS` (outer semantic cycles) |
| `L2_ROUNDS` | Replaced by **`NAGINI_REPAIR_CAP`** usage in Phase B (shared pool) |
| `L3_ROUNDS` | Same pool + **`NAGINI_REPAIR_FINAL_FLOOR`** for Phase D |

Exact numeric defaults (e.g. 5 vs 8) — **match current totals** or tune after first green run; document in PR.

## 9. Done criteria

- [ ] Critic is not invoked until Nagini translation gate passes for that candidate lineage.
- [ ] Semantic loop and Nagini final verify are sequential as in §3.
- [ ] Nagini repair attempts in B and D draw from one cap with documented floor behavior.
- [ ] `run_summary.json` / `verification_log.txt` remain the primary audit trail; new fields documented in `NagV/README` if present.
- [ ] Prompts updated so formalizer/repair/critic match §6.3.

---

**Status:** Ready for implementation when you approve this plan (or adjust §5 floor semantics / outcome enums). No code changes are implied until you greenlight execution against this document.
