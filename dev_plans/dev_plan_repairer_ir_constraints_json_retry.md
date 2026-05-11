# Dev plan: Repairer IR shape prompts + JSON parse retry (v1)

## Scope (this plan only)

1. **Prompt tightening** — **Repairer_Piv** (semantic + structural) and **Pivot critic** instructions so the LLM stops advising or emitting **IR shapes the Pydantic / compile layer rejects**, with emphasis on **PREEMPTION** and other **single-slot vs multi-value** v1 rules.
2. **Retry on repairer JSON parse failure** — If the repairer’s first reply is not parseable as a JSON object (e.g. truncation, junk around the object), **one bounded follow-up** call with an explicit “fix your JSON” instruction so a **transient formatting failure does not consume a full repair round** in the operator’s headspace.

**Explicit non-goals (out of scope here):** merging tester into repairer handoff; pre-Pydantic normalization of invalid IR; CLI messaging changes; IR schema extensions (e.g. list-typed `target_rule_id`); constrained decoding / response_schema from the vendor API.

## Problem

- **Semantic repair** after critic DRIFT often targets **multi-bypass** NL with a **single PREEMPTION** row; v1 allows **`target_rule_id` only as a single string**. The model emits lists or composite targets → **validation error** → repair discarded → critic sees the same DRIFT again.
- **Occasional** repair replies are **syntactically invalid JSON** (`Unterminated string`, etc.) → parse throws → **no rule update**, same as above.
- The **critic** narrates “bypass A and B” in natural language; that text is folded into **findings** / **notes** / **audit_trail** and steers the repairer toward **invalid shapes** unless the critic is aligned with v1 limits.

## Goals

- Document **normative v1 shape rules** in **both** repairer prompts (and a **short** critic block) so recommendations and patches use **only** encodings the loader accepts.
- Add **at least one retry** (configurable cap) when **`parse_json_object`** fails on the repairer response, using a **follow-up prompt** that includes the parse error (trimmed) and demands **only** `{ "rules": [...], "change_summary": [...] }`.

## Design

### A. Prompt changes (IR constraints)

**Shared principles to state verbatim in intent (not necessarily identical prose):**

- **`PREEMPTION`:** `target_rule_id` is **exactly one string** (a concrete `rule_id` such as `R0001`). It **must not** be an array, object, or comma-separated pseudo-list. To bypass **multiple** earlier rules under the **same** `preempting_condition`, emit **multiple `PREEMPTION` rules** (one row per target), reusing the same condition text / structure on each—do not invent a “multi-target” field.
- **`PREEMPTION` targets:** Must reference an **earlier** **non-`PREEMPTION`** rule in the same policy (existing structural prompt already mentions this; keep and cross-link).
- **Pathway / synthetic doc:** The repairer **outputs rules only**; generated `synthetic_en.md` follows the IR. Remind the model: **do not** assume `must_satisfy_all` includes `PREEMPTION` ids; fixes are **rule JSON**, not free editing of pathway markdown.
- **Other one-slot vs many (high value, concise list):**
  - One `rule_id` per rule object; no duplicate ids.
  - `LOGICAL_IMPLICATION`: one `trigger_condition` and one `required_condition` (each may be compound `and`/`or`/`not` trees—**do not** substitute parallel top-level arrays of requirements).
  - `SET_INCLUSION`: `constant_array` is the allowed list; **`target_rule_id`-style fields are not lists of rule ids** on non-PREEMPTION templates.
  - Any field that the **extractor contract** defines as a scalar must remain a scalar unless the **closed `pivot_pipeline.ir` model** says otherwise.

**Files:**

| File | Change |
|------|--------|
| `NagV/pivot_pipeline/prompts/repairer_piv_semantic.md` | New subsection **“v1 IR shape (normative)”** covering PREEMPTION + bullets above; point semantic repair at **minimal edits** that stay valid. |
| `NagV/pivot_pipeline/prompts/repairer_piv_structural.md` | Expand or merge with same **normative** PREEMPTION / single-slot list; structural mode is the **compile-error** path—emphasize “never fix by inventing illegal types.” |
| `NagV/pivot_pipeline/prompts/pivot_critic.md` | Short **“Recommendations and drift descriptions”** note: when NL implies bypass of **several** rules, describe fixes in terms of **several `PREEMPTION` rules** (one target each), **not** a single rule with multiple targets or non-schema fields. Critic output stays **JSON `CriticReport`** only; no new fields required. |

**Review:** Optionally diff against `extractor.md` / `v1_policy_encodability_contract.md` for one cycle so the three prompts don’t contradict each other.

### B. JSON parse retry (repairer only)

**Where:** `NagV/pivot_pipeline/repairer_piv_agent.py` — shared helper used by `run_repairer_piv_structural` and `run_repairer_piv_semantic`.

**Behavior:**

1. Call LLM with existing composed prompt (unchanged first attempt).
2. Try `parse_json_object(raw)`.
3. **If parsing fails:** If retry budget allows, call LLM again with a **second** composed message:
   - Include a fixed header, e.g. **“Your previous output was not valid JSON.”**
   - Include **trimmed** error / snippet (cap chars to avoid prompt blow-up; no full unbounded raw dump).
   - Require **exactly** one JSON object with keys **`rules`** and **`change_summary`**; no markdown fences, no prose before/after.
   - **Do not** resend the giant payload twice if avoidable: either (preferred) **append** a short corrective user block after the original prompt in one string, or resend payload once in the follow-up—pick one approach and document it (token tradeoff).

**Configuration:**

- Env e.g. **`PIVOT_REPAIRER_JSON_PARSE_RETRIES`** — default **`1`** (meaning **one** retry after the first failure = at most **two** LLM calls per repair attempt). Max cap in code (e.g. 3) to prevent runaway spend.

**Out of scope for this retry:** Pydantic / `RepairerPivOutput.model_validate` failures (invalid IR that is **valid JSON**) — those are **semantic/structural** issues; addressing them via a second prompt is a **separate** follow-up plan unless we explicitly extend this plan.

**Telemetry:** Append to `repairer_piv_*_trace.jsonl` a flag **`json_parse_retry_used`: true** when the second call succeeded, for debugging.

### C. Tests

- **Unit tests** (no live LLM): mock `llm` that returns invalid JSON on first call and valid `RepairerPivOutput`-shaped JSON on second; assert **`run_repairer_piv_semantic`** / **`run_repairer_piv_structural`** return validated output and that **two** calls occurred.
- **Unit test:** mock that always returns bad JSON; assert raises (or clear outcome) after exhausting retries—match chosen behavior (raise vs return signal—prefer **raise** consistent with today’s `parse_json_object` failure).

### D. Documentation

- **`.env.example`** (NagV or repo root as the project already documents pivot env): one commented line for `PIVOT_REPAIRER_JSON_PARSE_RETRIES`.

## Rollout order

1. Land **prompt** updates (repairer ×2, critic) — low risk, immediate alignment benefit.
2. Land **retry helper** + env + trace field + **tests**.
3. Manual smoke: force malformed repair output locally (mock or temporary break) and confirm retry path fires once.

## Risks

- **Token cost:** Second LLM call doubles worst-case cost per repair attempt; cap retries low.
- **Retry loop with persistent bad JSON:** Still fails after N tries; operator experience improves only for **recoverable** glitches.
- **Critic wording** that is too long may dilute focus; keep the multi-PREEMPTION guidance **brief**.

## Status

**Done** — Normative IR blocks in `repairer_piv_semantic.md`, `repairer_piv_structural.md`, `pivot_critic.md`; `PIVOT_REPAIRER_JSON_PARSE_RETRIES` + parse-retry in `repairer_piv_agent.py`; `json_parse_retry_used` in trace; `pivot_pipeline/tests/test_repairer_piv_agent.py`; `.env.example` line.
