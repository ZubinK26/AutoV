# Signature and Glossary Drafting Workflow

A specification for the upstream stage of the pipeline that produces `signature.py` and `glossary.md` from `rules.txt` (and optionally a domain notes file). This workflow runs before the formalization phase described in the main project specification. Its outputs are inputs to the rest of the pipeline.

This document tells Cursor how to implement signature drafting, glossary drafting, and the human review checkpoints between them. Prompts for the LLM agents are not in this document; they will be provided as a separate prompts artifact.

---

## 1. Where this workflow sits

The main project specification's Phase 1 (Formalization) assumes `signature.py`, `glossary.md`, `tools.json`, and fixtures already exist when the orchestrator starts. This workflow is what produces the first three of those (fixtures remain handled by the test-case generator role described in the main spec).

The full lifecycle for a fresh domain becomes:

```
Phase 0a — Signature drafting (this spec, sections 3-5)
Phase 0b — Glossary drafting (this spec, sections 6-7)
Phase 1   — Formalization (main project spec)
Phase 2   — Consistency check (main project spec)
Phase 3   — Runtime gating (main project spec)
```

Phase 0a and 0b are sequential: glossary drafting depends on signature being finalized, because every glossary entry references a signature symbol. Running them in parallel would create coordination issues and entry/symbol mismatches.

---

## 2. Inputs and outputs of Phase 0

**Required inputs:**
- `rules.txt` — the natural-language rules file. The user provides this.
- `tools.json` — declared tool calls. May be authored by the user before Phase 0 or co-drafted with the signature (see section 4.2).

**Optional inputs:**
- `domain_notes.md` — free-form text the user provides describing context the rules don't cover (typical numeric ranges, business conventions, edge cases the LLM wouldn't otherwise know). Improves drafting quality but not required.
- A reference signature from a previous domain — used as a few-shot example. Improves drafting consistency.

**Outputs of Phase 0a (signature drafting):**
- `signature.py` — verified-syntactically, reviewed by human, ready for Phase 1.
- `signature_draft_log.jsonl` — full record of drafter, critic, and refiner outputs for audit.

**Outputs of Phase 0b (glossary drafting):**
- `glossary.md` — verified-syntactically, reviewed by human, ready for Phase 1.
- `glossary_draft_log.jsonl` — full record of glossary agent output.

If `tools.json` is co-drafted, it is also a Phase 0a output.

---

## 3. Signature drafting architecture

Three LLM agents working sequentially, plus programmatic checks and human review.

### 3.1 The agents

**3.1.1 Signature Drafter.** Reads `rules.txt`, optional `domain_notes.md`, and optional reference signature. Produces an initial draft of `signature.py` plus, if `tools.json` was not provided, a draft `tools.json`. The drafter's task is **atom extraction**: identifying what entities, fields, enums, tool parameters, and (optionally) helpers are needed to express the rules under the signature-as-grammar interpretation. Composition is the formalizer's job in Phase 1, not the drafter's. The drafter does not produce rule expressions.

**3.1.2 Signature Critic.** Reads `rules.txt`, the drafter's draft signature, and the drafter's draft `tools.json` (if applicable). Produces a structured critique listing concerns by category: missing fields, surplus fields, suspicious bounds, incomplete enums, naming convention violations, helper coverage issues, and cross-artifact mismatches between signature and `tools.json`. The critic does not propose fixes; it only identifies issues.

**3.1.3 Signature Refiner.** Reads the original rules, the drafter's draft, the critic's critique, and (optionally) `domain_notes.md`. Produces a refined signature addressing the critique's findings. The refiner is the only agent that produces final-form output; the drafter's output is intermediate.

### 3.2 Why three agents instead of one or two

The literature on LLM-based ontology and schema extraction supports three-stage refinement over single-pass for moderately complex schemas. Self-critique by a single LLM tends toward sycophancy. Two-stage (drafter + combined critic-refiner) mixes "what's wrong" and "how to fix it" in one prompt, which empirically reduces both critique quality and fix quality. Three-stage forces explicit reasoning at each step.

The cost of three stages is three LLM calls instead of one. For the signature stage of a single domain, this is negligible — typically run once per domain.

### 3.3 Sequencing within Phase 0a

```
1. Drafter LLM produces signature draft + (optional) tools.json draft
2. Programmatic structural self-check on the draft (section 5)
   2a. If structural failures: route back to Drafter with errors annotated, retry up to 3 times
   2b. If structural pass: continue
3. Critic LLM produces critique against the structural-passing draft
4. Refiner LLM produces refined signature addressing critique
5. Programmatic structural self-check on the refined signature (section 5)
   5a. If structural failures: route back to Refiner with errors, retry up to 3 times
   5b. If structural pass: continue
6. Human review checkpoint (section 5.4)
7. After human approval: signature is finalized; Phase 0b begins
```

The structural self-check runs twice (after drafter, after refiner) because either agent can introduce structural errors. Running it after both catches errors at the cheapest possible repair point.

### 3.4 Drafter output expectations

The drafter produces:
- A populated `signature.py` matching the eight-section structure from the signature template.
- Bounds for every numeric field, marked with a confidence flag. The drafter is required to declare bounds even when uncertain; uncertain bounds are flagged for human review.
- Enum value lists as comprehensive as the rules support, marked with a completeness flag (`comprehensive` if the drafter believes the enum is complete, `partial` if it suspects more values exist that the rules don't mention).
- A draft `tools.json` if and only if one was not provided as input.
- A short rationale per declared symbol explaining what NL phrase or rule motivated it. Stored alongside the signature in a separate `signature_rationale.json` file, used by the critic.

### 3.5 Critic output expectations

The critic produces a structured JSON document with sections:

- **missing_fields**: fields the critic believes the rules require but the drafter omitted.
- **surplus_fields**: fields the drafter declared that no rule appears to need.
- **suspicious_bounds**: numeric bounds the critic believes are unreasonably tight or loose.
- **incomplete_enums**: enums the critic believes are missing values, with reasoning.
- **naming_violations**: symbols violating the naming conventions in the signature template.
- **helper_concerns**: helpers that look semantically wrong, helpers that should exist but don't.
- **tools_signature_mismatch**: parameters in `tools.json` that don't have corresponding `<tool>_call_<param>` symbols in the signature, or vice versa.
- **cross_section_inconsistencies**: e.g., `TOOL_DEPENDENCIES` references a symbol not declared elsewhere.
- **confidence_per_concern**: each finding tagged high / medium / low confidence.

Empty sections are allowed and expected — most signatures won't have issues in every category.

### 3.6 Refiner output expectations

The refiner produces:
- A revised `signature.py` addressing each critic finding it agrees with.
- A `refiner_decisions.json` log explaining for each critic finding whether the refiner accepted, partially accepted, or rejected the finding, with reasoning.

The refiner is allowed to reject critic findings if it believes the critique is wrong. The decision log makes the disagreement visible to the human reviewer.

---

## 4. Drafting `tools.json` alongside the signature

Two paths.

### 4.1 User-provided `tools.json`

If the user provides `tools.json` before Phase 0a, the drafter treats it as a fixed input. The signature must be consistent with the tool-parameter structure declared there: every gated tool's parameters appear as `<tool>_call_<param>` symbols in the signature.

### 4.2 Co-drafted `tools.json`

If the user does not provide `tools.json`, the drafter infers it from the rules. Inference targets:
- Tool names mentioned in the rules (e.g., "a refund call requires…" → tool name `apply_refund`).
- Parameters mentioned in connection with each tool (e.g., "the proposed amount" → parameter `amount_pence`).
- Whether each tool is gated, defaulting to gated unless the rules indicate otherwise (read-only lookups are typically not gated).

Co-drafted `tools.json` is treated as draft on equal footing with the signature: it goes through the critic and refiner stages, structural self-check, and human review.

### 4.3 Convention for which approach is taken

The orchestrator infers the path from input presence: if `tools.json` exists at workflow start, take 4.1; otherwise take 4.2. No explicit configuration flag.

---

## 5. Structural self-check

A programmatic checker that runs on draft and refined signatures. No LLM. Produces a `signature_check_report.json` with pass/fail and itemized findings.

### 5.1 What the self-check verifies

- The file parses as valid Python.
- All eight sections are present in the order required by the signature template (sections may be empty if optional).
- No statements outside the eight allowed sections (no script-level code beyond declarations).
- Imports are restricted to `cpmpy as cp` plus anything explicitly declared in section 1.
- Every variable name follows the naming convention for its section (UPPER_SNAKE_CASE for enums and dimensions, lower_snake_case with entity prefix for fields, etc.).
- Every CPMpy variable's `name=` argument matches its Python variable name.
- Every numeric bound is an explicit integer; no `None`, no expressions.
- No field is declared twice under different names.
- Every symbol referenced in `TOOL_DEPENDENCIES` is declared in sections 2-6.
- Every gated tool in `tools.json` appears as a key in `TOOL_DEPENDENCIES`, and vice versa.
- Every parameter declared for a gated tool in `tools.json` corresponds to a `<tool>_call_<param>` symbol in section 5 of the signature.
- The helper dependency graph (section 6) is acyclic.
- `DOMAIN_DIMENSIONS` and `TEST_SHAPE_BOUNDS` are present iff section 4 (vector fields) is non-empty.
- Every symbolic dimension referenced in section 4 is declared in `DOMAIN_DIMENSIONS`.

### 5.2 What the self-check does not verify

- Whether bounds are *correct* for the domain (e.g., whether 10_000_000 is the right upper bound for transaction amounts).
- Whether enum value lists are *complete* (whether more values exist in the real world).
- Whether fields are *missing* relative to the rules' actual semantic needs.
- Whether helpers capture the right semantics.

These are domain-knowledge questions the structural check cannot answer. They are the responsibility of the critic LLM and the human reviewer.

### 5.3 Behavior on failure

The self-check returns a structured failure list. The orchestrator routes the failure back to the agent that produced the failing output (drafter or refiner) with the failure list as additional context. Up to 3 retries per agent. If all retries fail, the orchestrator escalates to human review with the full failure list and the agent's outputs, and Phase 0a halts.

### 5.4 Human review checkpoint

After the refiner's output passes the structural self-check, the orchestrator presents the refined signature, the `tools.json` (whether provided or co-drafted), the `refiner_decisions.json`, and the original `rules.txt` side by side for human review.

The reviewer's responsibilities:
- Confirm bounds are reasonable.
- Confirm enum value lists are complete.
- Confirm no fields are missing relative to the rules.
- Confirm helpers (if any) capture intended semantics.
- Confirm `tools.json` correctly identifies gated and non-gated tools.

The reviewer can edit any of the artifacts directly. Edits are recorded in a `human_review_diff.json` for the audit log.

The reviewer signals approval by setting a `phase_0a_approved: true` flag in a workflow state file. The orchestrator does not advance to Phase 0b until approval is recorded.

---

## 6. Glossary drafting architecture

Glossary drafting is a separate downstream stage with a simpler architecture: one LLM agent plus a structural self-check plus human review.

### 6.1 Why one agent instead of three

Glossary entries are individually simpler than signatures. Each entry describes one symbol; there are no cross-entry dependencies, no global structure to validate beyond completeness, no bounds or enum completeness questions to debate. The three-agent loop adds cost without commensurate benefit at this stage.

The literature on LLM-based glossary and definition generation supports single-pass with structural verification for tasks at this complexity level.

If, after using the pipeline on multiple domains, glossary quality turns out to be a frequent source of formalization drift, a critic-refiner loop can be added in v2. For v1, single-agent is the right cost-quality tradeoff.

### 6.2 The agent

**Glossary Drafter.** Reads `signature.py` (the finalized version from Phase 0a), `rules.txt`, and (optionally) `domain_notes.md`. Produces `glossary.md` with one structured entry per declared symbol in the signature.

The drafter is told explicitly:
- Every declared symbol in sections 2-6 of the signature gets one glossary entry.
- Each entry describes what the symbol represents in domain terms, distinct from its declaration.
- For enums, each integer code's meaning is described.
- For helpers, the underlying fields and the condition the helper captures are both named.
- Where the rules use specific NL phrases that map to a symbol, those phrases are listed as `example_nl_phrases` in the entry.
- The output is the structured format described in section 6.4 below, not free prose.

### 6.3 Why finalized-signature is the input, not draft-signature

The glossary describes specific declared symbols. If the signature changes after the glossary is drafted, the glossary becomes stale. By drafting the glossary against the *finalized* signature (post-human-approval from Phase 0a), the alignment is guaranteed.

This is also why Phase 0a and 0b are sequential, not parallel.

### 6.4 Structured glossary format

The glossary file is YAML or equivalent structured format. Each entry is keyed by the signature symbol name and contains:

```yaml
<signature_symbol_name>:
  type: <enum | scalar_field | vector_field | tool_parameter | helper>
  description: <2-4 sentences describing what the symbol represents>
  value_meanings:                # required for enums and enum-coded fields
    <integer>: <description>
    ...
  derives_from:                  # required for helpers
    - <signature_symbol_1>
    - <signature_symbol_2>
  example_nl_phrases:            # 2-5 phrases from the rules that map to this symbol
    - <phrase>
    - <phrase>
```

The structure lets the glossary self-check programmatically verify completeness and quality.

### 6.5 Glossary self-check

A programmatic checker, no LLM. Verifies:

- Every signature symbol from sections 2-6 has a glossary entry.
- Every glossary entry corresponds to a signature symbol (no orphan entries).
- Every entry has a non-empty `description` of at least 20 characters.
- Every enum entry has `value_meanings` with one description per declared integer code.
- Every helper entry has `derives_from` listing at least one signature symbol that exists in the signature.
- Every entry has at least 2 `example_nl_phrases`, each at least 5 words long.

The minimum-length checks are crude but catch the "glossary entry that says nothing" failure mode that hurts formalization most.

### 6.6 Behavior on failure

If the self-check finds gaps (missing entries, sparse descriptions, incomplete enum value meanings), the orchestrator routes back to the Glossary Drafter with the gaps annotated. Up to 3 retries.

### 6.7 Human review checkpoint

After the self-check passes, the human reviewer reviews the glossary. Responsibilities:

- Confirm descriptions accurately reflect the domain.
- Confirm enum value meanings are correct (ordering, semantics).
- Confirm `example_nl_phrases` actually appear in the rules and map to the right symbol.

The reviewer can edit entries directly. Edits are recorded in a `glossary_human_review_diff.json` for audit.

Approval signaled by `phase_0b_approved: true` in the workflow state file. Phase 1 begins on approval.

---

## 7. Cognitive separation between signature and glossary drafting

The intent of separating Phase 0a from 0b is that no single LLM agent or human reviewer is asked to do signature work and glossary work in the same context. This is deliberate.

Specifically:

- The Signature Drafter, Critic, and Refiner are not asked to write descriptions. Their entire focus is atom extraction and bound estimation.
- The Glossary Drafter is not asked to make signature decisions. The signature is fixed by the time the glossary stage starts.
- The human reviewer for Phase 0a is asked to confirm signature decisions only. The reviewer for Phase 0b is asked to confirm glossary decisions only. (These can be the same person; the separation is in the review checklist they're given, not in their identity.)
- Few-shot examples for the Signature Drafter show only signatures, never glossaries. Few-shot examples for the Glossary Drafter show only glossaries against signatures, never the rules-to-signature path.

This separation is what lets each agent and reviewer focus narrowly. The cost is that Phase 0 has more stages than a single combined approach. The benefit is each stage is simpler, smaller in prompt context, and produces higher-quality output. The literature on LLM agentic decomposition is consistent on this point.

---

## 8. LLM roles introduced by this workflow

Four new roles, all called as functions; the orchestrator drives control flow. Prompts will be provided as a separate prompts artifact and are out of scope for this document.

| Role | Phase | Required? | Temperature | Notes |
|---|---|---|---|---|
| Signature Drafter | 0a | yes | 0.0 | Produces draft signature + optional draft tools.json. |
| Signature Critic | 0a | yes | 0.0 | Produces structured critique. |
| Signature Refiner | 0a | yes | 0.0 | Produces refined signature + refiner_decisions.json. |
| Glossary Drafter | 0b | yes | 0.0 | Produces structured glossary against finalized signature. |

These four are additional to the four LLM roles in the main project specification (Formalizer, Back-translator, Diagnoser, Test-case Generator), bringing the total to eight LLM roles in the full pipeline.

---

## 9. File layout additions

Adding to the file layout in the main project spec:

```
project/
  pipeline/
    drafting/
      signature_drafter.py        # LLM-driven (Drafter)
      signature_critic.py         # LLM-driven (Critic)
      signature_refiner.py        # LLM-driven (Refiner)
      glossary_drafter.py         # LLM-driven (Glossary Drafter)
      structural_check_signature.py   # programmatic
      structural_check_glossary.py    # programmatic
      human_review_gate.py        # programmatic, reads workflow state file
    orchestrator.py               # extended with Phase 0a and 0b states
  llm/
    prompts/
      signature_drafter.md        # to be provided separately
      signature_critic.md         # to be provided separately
      signature_refiner.md        # to be provided separately
      glossary_drafter.md         # to be provided separately
  domains/
    <domain_name>/
      rules.txt                   # user-provided
      domain_notes.md             # user-provided, optional
      tools.json                  # user-provided OR co-drafted in Phase 0a
      signature.py                # output of Phase 0a
      glossary.md                 # output of Phase 0b
      signature_rationale.json    # output of Phase 0a
      refiner_decisions.json      # output of Phase 0a
      signature_draft_log.jsonl   # full audit log of Phase 0a
      glossary_draft_log.jsonl    # full audit log of Phase 0b
      human_review_diff.json      # output of Phase 0a human review
      glossary_human_review_diff.json  # output of Phase 0b human review
      workflow_state.json         # tracks phase_0a_approved and phase_0b_approved
      fixtures/                   # produced later, in Phase 1
```

---

## 10. Build order recommendation for Cursor

This workflow is buildable as a vertical slice independent of the main project spec's slices. Recommended order if building Phase 0 alongside Phases 1-3:

1. **Slice 0.1: Structural self-checkers (signature and glossary), no LLMs yet.** Test against hand-written valid and invalid signatures and glossaries. Confirms the validation logic works. ~0.5 day.
2. **Slice 0.2: Signature Drafter alone.** Single-agent drafting with retry-on-structural-failure. Test on the example refund domain. ~0.5 day.
3. **Slice 0.3: Add Critic and Refiner.** Now full three-agent loop. Test on refund domain and check that critic finds something to critique on a deliberately-degraded draft. ~1 day.
4. **Slice 0.4: Glossary Drafter.** Single-agent against finalized signature. ~0.5 day.
5. **Slice 0.5: Human review gate + workflow state file + audit logs.** Now end-to-end Phase 0 runs with human checkpoints. ~0.5 day.

Total: ~3 days to get full Phase 0 running. This is independent enough of the main project spec that it can be built in parallel by a separate developer or in a separate branch, then integrated.

---

## 11. Out of scope for v1

- Glossary critic-refiner loop (single-agent for v1, expand to three-agent if quality issues arise).
- Cross-domain signature reuse / library composition.
- Live editing of signature or glossary mid-pipeline (changes require restarting Phase 0).
- Automated detection of when a signature should be updated based on new rules added to a finalized policy.
- Multi-language glossaries.

---

## 12. Success criteria for Phase 0

1. Given a fresh `rules.txt` for the example refund domain (no human pre-authored signature), the workflow produces a signature that passes structural self-check, an aligned glossary, and is judged by a human reviewer to require fewer than three substantive edits.

2. The Critic flags at least one real concern when given a deliberately-degraded draft (e.g., a draft with one missing field or one wrong enum coding).

3. The structural self-checks correctly identify all hand-injected structural violations in an adversarial test set.

4. Phase 0 outputs are sufficient for Phase 1 (Formalization) to proceed without modification.

5. The same workflow runs without code changes on a second domain (e.g., a small scheduling or guardrails policy) given only `rules.txt` and `domain_notes.md`.

The fifth criterion is the actual generality test, mirroring the main project specification's success criterion 9. Phase 0 must be domain-agnostic.
