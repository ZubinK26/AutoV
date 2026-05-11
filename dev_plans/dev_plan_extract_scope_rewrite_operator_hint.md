# Dev plan: operator hint for extract ABORT scope-rewrite loop (v1)

## Problem

On **`ExtractAbort`**, `extract_rules_with_abort_rewrite` (`extract_rewrite_loop.py`) calls **`run_scope_rewrite`** up to **`PIVOT_SCOPE_REWRITE_MAX_PROPOSALS_PER_LINE`** times. The operator may **reject** a proposal (**`n`**) because the LLM misunderstood stable policy facts (e.g. treating **“Rule 1” / “Rule 4”** as literal NL tokens instead of **`rule_id`** references **`R0001` / `R0004`**), but **successive proposals may repeat the same mistake** with no channel to steer the model.

## Goal

Allow the operator to supply **optional free-text feedback** after rejecting a scope-rewrite proposal (or optionally before accepting, if we want symmetry—**start with post-reject only** to limit UX complexity). That hint is passed into the **next** **`run_scope_rewrite`** call so the LLM can correct course.

**Hard requirement:** The model must treat the hint as **untrusted guidance**. It **must not** follow hints that conflict with **`v1_policy_encodability_contract`**, invent **`template_class`** values, ask for out-of-schema IR, or override safety semantics. In those cases it should **silently disregard** the offending parts and proceed as if no hint (or document disregard in **`fidelity_notes`**—pick one behavior and test it; **prefer no prose about “ignoring user” in rewritten_line**; optional one-line in **`fidelity_notes`** only if useful for audit).

## Non-goals (v1)

- Hints on **schema-repair** (`extract_schema_repair.md`) or **post-extract** critic/tester loops (separate future work).
- Natural-language “approval” of illegal encodings.
- Persisting hints across **different** ABORT lines unless trivially cheap (default: hint applies only within the **current line’s** proposal sub-loop).

## UX design

**After** the operator answers **`n`**, **`no`**, or **`skip`** (anything other than **`y`/`yes`**):

1. Prompt once, e.g.  
   `Optional hint for the next proposal (Enter = none; max N chars): `
2. Read single-line (or bounded multi-line with explicit end—**v1: single line** to keep TTY simple). Enforce **`PIVOT_SCOPE_REWRITE_HINT_MAX_CHARS`** (new env, default e.g. **500**, cap **2000** in code).
3. Store `operator_hint` on the JSONL record for that rejection event.
4. On the **next** iteration of the inner `for prop_ix ...` loop, if `operator_hint` is non-empty, pass it into **`run_scope_rewrite(..., operator_hint=...)`**.

Clear the stored hint after it has been **consumed** by one `run_scope_rewrite` call so stale hints do not repeat forever—unless the operator **rejects again** and supplies a **new** hint (fresh input).

**Optional shortcut:** Allow **`h:text`** on the same line as **`n`** later (defer to v2 unless trivial).

## Implementation sketch

### 1. `run_scope_rewrite` (`extract_scope_rewrite.py`)

- Add optional parameter **`operator_hint: str | None = None`**.
- In **`scope_rewrite.md`**, add placeholder **`<<<OPERATOR_HINT>>>`** (default string **`(none)`** when empty).
- Append a **normative** subsection (in the markdown, not only contract) stating:
  - Operator hint is **optional context** (e.g. clarify **`rule_id`** usage, variable names, or ambiguity).
  - **Must ignore** any part of the hint that would require **non-v1** constructs, new **`template_class`**, illegal **PREEMPTION** targets, etc.
  - Output must still be **valid v1-encodable** rewrite JSON per existing schema.

### 2. `extract_rewrite_loop.py`

- After non-accept, call **`input_fn`** for optional hint (only when interactive; if `input_fn` is mock/non-TTY in tests, pass through).
- Thread **`operator_hint`** into **`run_scope_rewrite`** on the following proposal.
- Extend **`extract_rewrite_log.jsonl`** records with **`operator_hint_submitted`** (string or null) on reject rows.

### 3. Observability

- Log hint length + hash (optional) if privacy/size matters—**v1: log raw hint** in JSONL (same sensitivity as other logs in `work_dir`).

### 4. Tests

- **Unit:** `run_scope_rewrite` prompt includes trimmed hint when provided (monkeypatch **`llm`** to capture prompt string).
- **Loop:** fake **`input_fn`** sequence: reject → hint → verify **`run_scope_rewrite`** called with hint once.
- **Contract:** optional **stub LLM** returning rewrite that violates contract should still be caught by downstream extract—hint must not disable validation (no change to validators expected).

## Rollout

1. Land **`scope_rewrite.md`** + **`run_scope_rewrite`** signature (backward compatible default `None`).
2. Wire **`extract_rewrite_loop`** + JSONL fields.
3. Document env **`PIVOT_SCOPE_REWRITE_HINT_MAX_CHARS`** in **`.env.example`** (one line).
4. Manual smoke: ABORT line → reject → hint mentioning **`R0004`** → expect next proposal alignment (best-effort; LLM not deterministic).

## Risks

- **Prompt injection:** treat hint as data; **normative ignore** rule reduces but does not eliminate risk.
- **Verbose operators:** cap length; truncate with notice in log.

## Status

**Done** — `run_scope_rewrite(..., operator_hint=...)`, `scope_rewrite.md` placeholder + normative block, `extract_rewrite_loop` post-reject hint + JSONL `operator_hint_submitted`, `PIVOT_SCOPE_REWRITE_HINT_MAX_CHARS`, tests in `test_extract_rewrite.py`.
