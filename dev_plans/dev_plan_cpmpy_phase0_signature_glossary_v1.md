# Dev plan: Phase 0 — signature & glossary drafting workflow (v1)

## Purpose

Implement **Phase 0a / 0b** as specified in:

- `CPMpy/Project_Spec/Project_Spec_Agents/04_signature_glossary_workflow.md` — agent roles, sequencing, structural self-checks, human gates, audit artifacts, file layout, build order, success criteria.

Phase 0 produces **`signature.py`**, **`glossary.md`**, and (when applicable) **`tools.json`**, so the existing **Phase 1** formalization pipeline (`01_project_specification.md` §2) can assume those inputs exist.

**Prompts:** Out of scope for this plan; they will be supplied separately and bound under `cpmpy_wfm_policy/llm/prompts/` per the workflow doc §9 (`signature_drafter.md`, `signature_critic.md`, `signature_refiner.md`, `glossary_drafter.md`). Implementation assumes **placeholder prompts** until the artifact arrives, but **schemas and orchestration** must be final from day one.

**Non-goals:** Per workflow §11 (glossary critic-refiner v2, cross-domain libraries, mid-pipeline live edit automation, multi-language glossaries).

---

## Guiding constraints (from product notes)

1. **Build structural self-check first (Slice 0.1).** No LLM agents until signature and glossary checkers exist and are tested on **hand-written** valid/invalid fixtures. Agents are evaluated *against* this ground truth; building agents first makes regression detection impossible.

2. **Critic output is schema-critical.** Section 3.5 defines the JSON shape (`missing_fields`, `surplus_fields`, `suspicious_bounds`, `incomplete_enums`, `naming_violations`, `helper_concerns`, `tools_signature_mismatch`, `cross_section_inconsistencies`, `confidence_per_concern`). Implement **strict Pydantic models** + **retry-on-malformation** (mirror formalizer JSON retry pattern: bounded attempts, log to `signature_draft_log.jsonl`). Loose critic JSON invalidates the Refiner contract.

3. **`refiner_decisions.json` is load-bearing.** Mandatory Phase 0a output: per critic finding, record accept / partial / reject + rationale so reviewers can distinguish **Refiner** vs **Critic** vs **Drafter** responsibility. Do not treat this as optional logging.

4. **Glossary format (§6.4).** Spec uses **structured YAML** (or equivalent) for machine-verifiable completeness. **Default implementation: follow the spec.** If the team later prefers prose glossaries, that is an explicit product change: trade **checkability** vs **LLM fluency**. Document that decision in ADR/workflow amendment, not silently in code.

5. **Success criterion 5 = generality bar.** Same spirit as main spec success criterion #9: the workflow must run **without code changes** on a **second domain** (e.g. small **scheduling** or **guardrails** policy) given `rules.txt` + optional `domain_notes.md`. Plan exit criteria include drafting Phase 0 end-to-end for **refund** *and* **second domain** as soon as Slice 0.5 is in place—not as a late add-on.

---

## Repository placement

Implement under the existing package (consistent with current tree):

```
CPMpy/policy_pipeline/cpmpy_wfm_policy/
  pipeline/
    drafting/
      structural_check_signature.py   # Slice 0.1
      structural_check_glossary.py    # Slice 0.1
      signature_drafter.py              # Slice 0.2+
      signature_critic.py               # Slice 0.3+
      signature_refiner.py              # Slice 0.3+
      glossary_drafter.py               # Slice 0.4+
      human_review_gate.py              # Slice 0.5
      phase0_state.py                   # workflow_state.json I/O (optional split)
      phase0_orchestrator.py            # Phase 0a/0b state machine (or extend cli)
    orchestrator.py                     # optional thin bridge: “run Phase 0 then Phase 1”
  llm/prompts/
    signature_drafter.md
    signature_critic.md
    signature_refiner.md
    glossary_drafter.md
```

Wire **package data** in root `pyproject.toml` for new `*.md` prompts (same pattern as existing formalizer prompts).

**CLI:** Add subcommands to `cpmpy_wfm_policy/cli.py`, e.g.:

- `phase0-check-signature` — run structural check only (stdin path → `signature_check_report.json`).
- `phase0-check-glossary` — glossary structural check only.
- `phase0-run` — full Phase 0a+0b with configurable `--skip-human` for CI (see Slice 0.5).

---

## Slice 0.1 — Structural self-checkers (no LLMs)

**Deliverables**

- `structural_check_signature.py`: implements §5.1 checks; emits **`signature_check_report.json`** (`pass`, itemized `findings[]` with stable codes for orchestrator routing).
- `structural_check_glossary.py`: implements §6.5 against finalized `signature.py` + glossary file (YAML parse → symbol coverage).
- **Test suite:** `CPMpy/policy_pipeline/tests/test_phase0_structural_*`:

  - **Valid:** `domains/refund_example/signature.py` (and glossary once YAML exists), hand-written minimal good fixtures.
  - **Invalid (adversarial):** inject each violation class from §5.1 / §6.5 (wrong section order, illegal import, mismatched `name=`, duplicate fields, cyclic helpers, orphan glossary keys, missing enum `value_meanings`, short `description`, etc.).
  - Success criterion **#3** from workflow §12: checker catches **all** hand-injected structural violations in the adversarial set.

**Dependencies:** `CPMpy/Project_Spec/02_signature_template.md` is normative for section layout and naming rules; keep checker rules in sync with template updates.

**Exit:** CI-green tests; no agent code merged without these tests governing agent output.

---

## Slice 0.2 — Signature Drafter (single agent + structural retry)

**Deliverables**

- LLM wrapper: load prompt, build user message from `rules.txt`, optional `domain_notes.md`, optional reference `signature.py` path, optional fixed `tools.json` (§4.1).
- Parse drafter output into:

  - `signature.py` string (or path write),
  - optional `tools.json` draft if absent at start (§4.2),
  - `signature_rationale.json` (§3.4).

- Orchestration step: **structural self-check** → on failure, append errors to context, **retry ≤ 3** (§3.3, §5.3).
- Append every attempt + metadata to **`signature_draft_log.jsonl`** (§2, §9).

**Tests:** Mock LLM returning canned drafts; verify retry loop and log shape. Smoke on **refund** `rules.txt` only after prompts exist (or deterministic stub).

---

## Slice 0.3 — Critic + Refiner (full Phase 0a loop)

**Deliverables**

- **Pydantic models** for Critic JSON exactly covering §3.5; empty lists allowed; `confidence_per_concern` keyed or parallel structure as prompt specifies—**normalize in code** to a canonical internal model.
- `signature_critic.py`: invoke critic, validate, retry on parse failure.
- `signature_refiner.py`: consume draft + critic + optional `domain_notes`; output refined `signature.py` (+ co-drafted `tools.json` if applicable) and **mandatory `refiner_decisions.json`** (§3.6).
- Second structural pass after refiner; refiner retry ≤ 3 on structural failure (§3.3).

**Tests**

- **Success criterion #2 (§12):** degraded draft fixture (e.g. missing field) → mocked critic returns at least one finding in expected section.
- Refiner mock produces decisions covering accept/reject/partial.

---

## Slice 0.4 — Glossary Drafter + glossary structural retry

**Deliverables**

- `glossary_drafter.py`: inputs finalized `signature.py`, `rules.txt`, optional `domain_notes`; output **YAML glossary** per §6.4 (file extension `glossary.md` per workflow §9 can still hold YAML — clarify in README; if tooling expects `.yaml`, prefer `glossary.yaml` only if spec amended).
- Self-check (§6.5) → retry ≤ 3; log to **`glossary_draft_log.jsonl`**.

**Tests:** Mock LLM; adversarial glossary vs checker.

---

## Slice 0.5 — Human review gate, workflow state, audit trail

**Deliverables**

- `workflow_state.json`: `phase_0a_approved`, `phase_0b_approved` (§5.4, §6.7).
- `human_review_gate.py` (or thin helpers): document expected reviewer artifacts; optional CLI that **prints** review bundle paths and blocks Phase 0b / Phase 1 until flags set (or `--auto-approve` / env **only for dev**, never default for production).
- **`human_review_diff.json`** / **`glossary_human_review_diff.json`**: format TBD minimal JSON (paths, timestamps, edited files, optional unified diff snippets)—spec asks to **record edits**; keep v1 simple but **non-empty** when edits exist.

**Integration**

- Document **handoff to Phase 1:** when `phase_0b_approved`, operator runs existing `cpmpy-policy-pipeline run` (or single “migrate” command that runs Phase 1).

---

## Second domain (success criterion 5)

**Early deliverable:** After Slice 0.5, add **`domains/<second_domain>/`** (vectors and/or global constraint per main spec direction—use `03_example_domain.md` / inventory-style sketch if available) with:

- User-authored `rules.txt` + `domain_notes.md` only (no pre-authored `signature.py`/`glossary.md` in the “cold start” test path).

**Exit test:** Run Phase 0 end-to-end (with human approval mocked in CI if needed) **without changing Python** beyond fixture paths; structural + schema tests pass. Manual run proves human reviewer can approve with &lt;3 substantive edits (workflow §12 #1/#5).

---

## Observability and failure modes

- All LLM calls: log inputs/outputs/latency/model to **`signature_draft_log.jsonl`** / **`glossary_draft_log.jsonl`** consistent with main pipeline `verification_log.jsonl` style where practical.
- Escalation: structural retries exhausted → halt Phase 0a with **actionable** report + last agent outputs (§5.3).

---

## Estimated effort (from workflow §10)

Roughly **~3 developer-days** for slices 0.1–0.5 after prompts land; Slice 0.1 should complete in **~0.5 day** if `02_signature_template` rules are already stable.

---

## Checklist before marking v1 done

- [ ] Slice 0.1 tests green; adversarial coverage complete.
- [ ] Critic schema strict + logged retries.
- [ ] `refiner_decisions.json` always written on successful Phase 0a refiner path.
- [ ] Glossary YAML check enforces §6.5.
- [ ] Refund + **second domain** cold-start Phase 0 exercised.
- [ ] README updated: Phase 0 CLI, file layout, human approval, link to `04_signature_glossary_workflow.md`.
