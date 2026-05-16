# Dev plan: pre-WFM **Scope Rewriter** (reference NL → pivot-ready plain NL)

## Problem

Real-world policy documents (prose, mixed structure, implicit context) often contain rules that **partially** fit the pivot stack (WFM → extract → v1 IR → Z3). Mixed-fit corpora create **rewrite friction**: many lines encode cleanly while outliers force abort loops, OUT_OF_SCOPE churn, or silent semantic drift. A **upstream normalization pass** can reduce that friction by producing a **single plain-text ruleset** written explicitly for the project’s expressivity gates, **before** Phase 0 WFM.

## Goal (v1)

Add a **Scope Rewriter** agent (generative module) that:

1. Takes **reference natural language** (e.g. one UTF-8 Markdown file), treated as **authoritative intent**, not as layout or boilerplate to preserve verbatim.
2. Rewrites it into **plain text** consisting of **one encodable-style rule per non-empty line** (same consumer convention as existing pivot NL inputs: comments `#` and blank lines ignored downstream; project parsing rules stay the single source of truth in code).
3. Honors **two strict objectives simultaneously**:
   - **Semantic fidelity:** preserve the meaning of the reference as closely as **pivot v1 semantics** allows (no silent strengthening/weakening; deltas must be explicit).
   - **Scope compliance:** align with the same **closed-world constraints** already used in pivot: `NagV/pivot_pipeline/prompts/v1_policy_encodability_contract.md`, extractor contract, WFM pivot cardinality (one line per logical rule in the deliverable), and practical WFM behavior (avoid constructs that systematically force OUT_OF_SCOPE or extract ABORT where a faithful surrogate exists).
4. When a clause **cannot** be expressed with full equivalence inside scope, the agent must:
   - Emit the **nearest compliant rewrite** anyway (no empty refusal).
   - Set a machine-readable **fidelity / scope flag** (see **Output contract**) so humans and automation can see partial compliance.

After generation, a **human editing loop** runs until the operator and the agent agree the corpus is ready; then the pipeline invokes **existing** pivot Phase 0 WFM on the agreed file.

## Non-goals (v1)

- No change to WFM Agents 1–3 core prompts beyond what already exists; Scope Rewriter is **before** WFM.
- No proof obligation: the rewriter **does not** guarantee extract or WFM success—only **improved alignment** with documented scope and traceable deltas.
- No automatic skip of human review for production-quality runs (optional dry-run / CI stubs may bypass the loop later).
- No obligation to preserve Markdown structure, headings, or tables; output is **plain rules text** unless we explicitly add a structured interchange format in a later revision.

## Relationship to existing pieces

- **Extract ABORT scope rewrite** (`extract_scope_rewrite`, `scope_rewrite.md`): line-local, triggered **after** extract fails. Scope Rewriter is **document-level**, **before** WFM, focused on **proactive** normalization.
- **Pivot WFM chunk footer / cardinality**: the rewriter should prefer outputs that already respect **one rule per line** and avoid “split one source sentence into many numbered obligations” when a single scoped line suffices—but it does not replace WFM; WFM remains the formal gate.
- **Semantic equivalence** is not decidable by software; the contract is **disclosed deltas + flags + human sign-off**.

## Design: artifacts and placement

Suggested layout (exact paths to be finalized in implementation):

- **Prompt:** `NagV/pivot_pipeline/prompts/scope_rewriter_pre_wfm.md` (or `WFM/adjacent` if we want cross-pipeline reuse—prefer `pivot_pipeline` to keep encodability contract nearby).
- **Module:** `NagV/pivot_pipeline/scope_rewriter_agent.py` (or `NagV/pre_wfm/`) exposing a small API: `run_scope_rewriter_round(reference_path, prior_output_path | None, operator_notes | None) -> ScopeRewriterResult`.
- **CLI:** e.g. `scope-rewriter` or `pivot-pipeline --pre-wfm-scope-rewrite` (decision: separate entry keeps pivot CLI smaller; a subcommand avoids proliferation—pick one in implementation).
- **Work directory** (per reference source, analogous to pivot runs):
  - `reference.md` (copy or symlink—optional)
  - `scope_rewriter_output/latest.nl` (or `.txt`)
  - `scope_rewriter_output/history/round_N.*` (optional)
  - `scope_rewriter_log.jsonl` (round metadata, model id, flags)

## Human-in-the-loop protocol (v1)

1. **Round 0:** Operator runs Scope Rewriter on reference file → model writes `latest` + structured sidecar (JSON next to output or embedded header—see contract).
2. **Review:** Operator reads plain text. They may edit **in place** (or replace file—implementation fixes the canonical path).
3. **Next round:** Operator types **ready** (or **no edits** if unchanged) at prompt → agent re-runs with **previous agent output + human-edited text** + optional short operator note (“ tightened rule 7 ”).
4. **Stop when** either:
   - **Human satisfied:** operator selects **accept** / **no further edits** and agent’s last message asserts **no remaining scope violations / no mandatory rewrites** (per contract), or
   - **Agent satisfied with human text:** agent returns **no diffs** and **fidelity_flags** all clear—or explicitly lists only optional polish (policy: human may still proceed).
5. Only after **explicit handoff step** should `pivot-pipeline --input …` use the **agreed** path as Phase 0 input (script may print the exact command).

Termination rules need crisp wording in the prompt (“stop oscillating”; max rounds env e.g. `SCOPE_REWRITER_MAX_ROUNDS`) to avoid infinite ping-pong.

## Output contract (machine-readable + plain NL)

Plain text body: **one rule per line**, no numbering required in file (downstream chunk formatting adds global numbering). Leading/trailing blanks stripped per line.

Sidecar (recommended JSON alongside `.nl`):

- `schema_version`
- `reference_sha256` / `output_sha256`
- `round_index`
- `fidelity_summary`: short string
- `lines`: optional per-line objects if we need granularity later; v1 may use **global flags only**
- `strict_equivalence_achievable`: `true` | `false`
- `partial_rewrites`: list of `{ "approximate_line_span": "…", "reason": "…", "nearest_rewrite_note": "…" }` when full equivalence was impossible
- `semantic_deltas`: list of strings (document-level and/or line refs)
- `model_metadata`: provider, model id, temperature (for audit)

If JSON is optional for v0.5, v1 should require it for automation and critic hooks later.

## Prompt engineering (best practices checklist)

The system prompt (and any user template) should:

1. **Role and task:** single paragraph: rewrite reference into pivot-ready plain rules; reference is intent source; output is consumable by existing parsers.
2. **Hard constraints:** inject or summarize **v1 encodability contract** (by file read at runtime, not stale paste)—same pattern as extract scope rewrite.
3. **Prohibited:** example-specific rules (“e.g. bonus points for homework 3”); no dataset leakage; no invented policy beyond reference.
4. **Ambiguity handling:** prefer explicit quantifiers and named entities; if reference is ambiguous, choose minimal interpretation and **state assumption** in `semantic_deltas`.
5. **Strict equivalence:** define “cannot express” relative to **v1**, not to English in general; require nearest rewrite + flag.
6. **Output discipline:** separate **human-readable body** from **JSON metadata** (fenced JSON block at end, or two files—implementation chooses; two files is safer for parsing).
7. **No chain-of-thought in user-visible body** unless we add a `reasoning_trace` field only in JSON (recommended off for production).
8. **Round loop:** when given “human edited version”, diff mentally against reference intent; only propose changes that **restore scope or fix human-introduced violations**; acknowledge human authority for stylistic choices that remain in scope.
9. **Length:** cap output size or chunk internal reasoning via contract sections to avoid token blowups; large references may require **chunked rewriter passes** (future phase—note under Open questions).

## Integration with pivot pipeline

- **Explicit phase:** Document in `README` / `Extract-Pivot.md`: recommended order `Scope Rewriter → pivot-pipeline (Phase 0 WFM)`.
- **Optional guard:** future `pivot-pipeline --require-scope-rewriter-metadata` could check for sidecar JSON with `strict_equivalence_achievable` and operator ack timestamp—out of scope for v1 minimal deliverable.
- **Env:** `GEMINI_*` shared with pivot; optional `SCOPE_REWRITER_MODEL` override.

## Testing strategy

- **Unit:** parse sidecar JSON; golden tests for “reference → expected flags” with **mocked LLM** returning fixture bodies.
- **Contract tests:** prompt file contains required sections / includes encodability path (smoke).
- **Manual:** one small reference MD + one messy real doc; verify human loop and then Phase 0 starts without excessive OUT_OF_SCOPE.

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Rewriter drifts from reference intent | Mandatory `semantic_deltas` + human sign-off; versioned sidecar |
| Rewriter contradicts WFM/extract anyway | Still allow WFM; rewriter reduces but does not eliminate friction |
| Prompt rot | Encodability injected from single file; rewriter prompt version in JSON |
| Ping-pong edits | Max rounds; prompt instructs agent to yield when human text is in-scope |
| Large documents exceed context | Phase 2: hierarchical or chunked rewrite with merge pass |

## Phased delivery

| Phase | Deliverable |
|-------|-------------|
| **P0** | Dev plan + prompt skeleton + JSON schema agreed |
| **P1** | `scope_rewriter_agent` module + CLI + one reference→output path + sidecar JSON |
| **P1b** | Prompt hardening (fidelity + encodability taxonomy + extended sidecar) — see [`dev_plan_scope_rewriter_prompt_hardening_v1.md`](dev_plan_scope_rewriter_prompt_hardening_v1.md) |
| **P2** | Interactive loop (`ready` / `accept` / operator notes) + log append |
| **P3** | Docs (`README` quickstart) + pytest mocks + optional `pivot-pipeline` handoff hint |
| **P4** (optional) | Chunked references; critic hook comparing reference hash to rewriter output |

## Open questions

1. **Single file vs directory** of references (appendices)?
2. **Language:** English-only v1 or bilingual operator notes?
3. **Legal / PII:** whether copies of reference in `work_dir` need redaction flags.
4. **Determinism:** temperature 0 default vs small creativity for paraphrase—default to **0** for auditability unless human asks for alternatives round.

## Done when (v1)

- Operator can run Scope Rewriter on a `.md` reference, complete a **bounded** human/agent loop, and obtain a **plain text file** suitable as `--input` to `pivot-pipeline` Phase 0.
- Sidecar records **strict_equivalence_achievable** and **partial_rewrites** when applicable.
- Prompt follows the checklist above and pulls encodability text from the repo **at runtime** (no stale duplication).
- Tests cover parsing and loop state without calling a live API.
