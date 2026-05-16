# Dev plan: Scope Rewriter — **policy spec / guardrails** input mode (vs reference corpus)

## What you want

**Input:** A single document that describes **guardrails, constraints, and rules** you intend to **express** within the pivot stack’s encodability scope — not necessarily already in “one line = one rule” plain NL, and not necessarily a frozen policy text to preserve verbatim.

**Job:** **Generate** `plain_rules` (same deliverable as today: newline-separated rules for Phase 0 WFM) that:

1. **Stays within** pivot v1 encodability (same contract injection as today).
2. Is **semantically as close as possible** to that description (intent fidelity), with honest disclosure where full equivalence is impossible.

**Output path:** Unchanged — `latest.nl` + `latest.json` sidecar consumed by `pivot-pipeline` like today.

## Is this already wired?

| Piece | Status |
|-------|--------|
| Artifact shape (`plain_rules`, sidecar, `latest.nl` / `latest.json`) | **Yes** — already WFM-ready |
| LLM stack (Gemini, JSON mode, contract append) | **Yes** |
| **Semantic contract** for the input | **No** — prompt is written for a **reference corpus** |
| **Explicit mode** in CLI / user message | **No** |

### Today’s mismatch (why “paste a spec” is only partial)

[`scope_rewriter_pre_wfm.md`](../NagV/pivot_pipeline/prompts/scope_rewriter_pre_wfm.md) frames input as **“Reference text — authoritative intent; do not invent obligations that are not supported by it.”** Coverage rules assume **every substantive obligation in the reference** maps to output or `partial_rewrites`. That optimizes **transcription / normalization** of an existing policy, not **expanding** a high-level guardrails doc into **concrete** in-scope lines when the spec is intentionally under-detailed.

So: you *can* paste a description today and often get something useful, but the **system is not authored or tested** for spec-as-primary-artifact, and the model is **actively discouraged** from **necessary concretization** that isn’t literally entailed by a sentence in the file.

## Goals (v1)

1. Add an explicit **`input_mode`** (names TBD) with at least:
   - **`reference_corpus`** — current behavior (line coverage vs source, minimal invention).
   - **`policy_intent_spec`** — description → generated in-scope rules; fidelity is to **stated intent**, not verbatim source span inventory.
2. Wire mode through **CLI** (`scope_rewriter_cli.py`) and **user message builders** (`build_user_initial`, `build_user_review`) in [`scope_rewriter_agent.py`](../NagV/pivot_pipeline/scope_rewriter_agent.py).
3. **Prompt forks** (same file with mode sections, or include snippets): for `policy_intent_spec`, replace “no invention / full coverage of source spans” with rules such as:
   - **Cover the intent** of every **stated** constraint in the spec (or explain omission in `semantic_deltas` / `partial_rewrites`).
   - **Concretize** only when needed for encodability — introduce **named scalar / finite disjunction** surrogates; document in `semantic_deltas`.
   - **Do not** add obligations **absent** from the spec (no “helpful” policy extras).
   - **Prefer** splitting into multiple lines over packing or hiding structure.
4. Optional **sidecar** field: `input_mode` string (and optionally `intent_fidelity_notes`) for downstream audit.
5. **Tests:** golden user-message snippets per mode; parser accepts new optional fields on `ScopeRewriterLLMOutput` if added.

## Non-goals (v1)

- Automatic validation that output “matches” the spec (still human + WFM).
- Multi-file spec merge or versioning.
- Changing WFM extract contracts.

## Design details

### CLI

- Add `--input-mode {reference_corpus,policy_intent_spec}` (default **`reference_corpus`** for backward compatibility).
- Docstring / `--help`: explain that `policy_intent_spec` is for guardrails / intent docs, not necessarily final NL.
- Optional env mirror: `SCOPE_REWRITER_INPUT_MODE` (last‑writer wins vs flag — document).

### User message shape

- `build_user_initial(..., input_mode=...)`:
  - **reference_corpus:** keep `## Reference document (full text)` + current semantics.
  - **policy_intent_spec:** use e.g. `## Policy intent specification (guardrails and constraints)` and a short system/preamble line: “You are realizing this specification as plain rules; the specification is authoritative for **what** to express, not for **verbatim wording**.”
- Review rounds: pass same mode; “reference” block title can stay neutral (“Authoritative input (unchanged)”) to avoid confusing the model.

### Prompt structure

- Single [`scope_rewriter_pre_wfm.md`](../NagV/pivot_pipeline/prompts/scope_rewriter_pre_wfm.md) with a clear **Mode: reference_corpus** / **Mode: policy_intent_spec** subsection at the top (or after role), each with:
  - Fidelity definition (source-span coverage vs intent coverage).
  - Invention boundary (forbidden vs allowed concretization).
- Shared tail: encodability taxonomy, JSON schema, contract injection unchanged.

### Sidecar / schema

- `ScopeRewriterLLMOutput.input_mode_echo: str | None` optional **or** rely on run record only — recommendation: record mode in **`run_scope_rewriter_round`’s `record` dict** from CLI args (ground truth), not only model echo.

## Verification

- Manual: same **spec-shaped** markdown under both modes; expect **policy_intent_spec** to produce **more explicit** rule lines and fewer “partial_rewrites” that only complain about “compression.”
- Regression: existing **reference** docs under **reference_corpus** behave as today (spot-check `Evaluation_RUles_Processed`-style files).

## Done when

- Flag + user message + prompt branch merged; README or pivot_pipeline README mentions both modes in one short paragraph.
- Tests cover message building and record contains `input_mode`.
- Operator can run:  
  `scope-rewriter --reference my_specs.md --work-dir ... --input-mode policy_intent_spec`

## Related

- [`dev_plan_scope_rewriter_prompt_hardening_v1.md`](dev_plan_scope_rewriter_prompt_hardening_v1.md) (fidelity + encodability taxonomy — applies to **both** modes with mode-specific fidelity definitions).
