# Dev plan — G1 & G2 orchestration (acceptance → handoff, Style-A loop)

**Scope:** Implementation work for **`development_plan_wfm_registry_e2e_demo.md`** items **G1** (automatic **`HandoffBundle`** at accept) and **G2** (merged NL → **Agent 1** re-entry **without** a separate manual CLI run).

**Out of scope for this file:** registry M4/M5 internals (already built). **G6 / G7 / G8 / G9** (curated menu, word cap, viewers, warm-registry script) are **in scope for** **`development_plan_wfm_registry_e2e_demo.md`** — tracked there; **not** “unplanned,” only **not implemented yet** in code.

**G1 implementation (registry stage):** **`registry_stage/wfm_acceptance_handoff.py`** — `WfmAcceptanceSnapshot` / `WfmAcceptanceLine`, `build_handoff_bundle`, `validate_handoff_roundtrip`, `write_handoff_bundle`, `acceptance_snapshot_from_jsonable` / `load_acceptance_snapshot`. (tests: **`registry_stage/tests/test_wfm_acceptance_handoff.py`**).

**G1 wiring + G2 implementation (orchestrator):** **`wfm_orchestration/`** — `wfm_acceptance_snapshot_from_agent_outputs` (Agent 2/3 text → snapshot), **`run_wfm_registry_e2e`** (console: Agents 1→2→3, accept or disagree → Agent 4 + Style-A merge → **automatic** Agent 1 re-entry, up to **4** outer passes; on accept → `build_handoff_bundle` → `run_bundle_through_registry`). CLI: **`python -m wfm_orchestration.cli`** (`--text` / `--file`, `--export`, `--handoff`, `--mock-resolve` for stub M4). Tests: **`wfm_orchestration/tests/test_snapshot_from_agents.py`**.

**Follow-up implementation (spec agreed; code not all landed in `wfm_orchestration` yet):**

| Item | What **`Agent_WFM.md`** / we agreed | What the **current** orchestrator does | Next step |
|------|-------------------------------------|------------------------------------------|-----------|
| **Agent 4 inner retries** | After disagreement, Agent 4 may use up to **3 retries** (tentative rewrites) in addition to the first exchange — see **Retry budget** in **`Agent_WFM.md`**. | **One** Gemini call to Agent 4 per disagree round. If the response has **no** valid ```wfm_patch``` or merge fails, the run **stops** (no automatic re-prompt of Agent 4 up to the spec budget). | Implement the **retry loop** around `call_agent4_gemini` + patch validation (same payload family), up to spec limits. |
| **O2 — Agent 3 “failed rewrite”** | **Agreed:** re-call Agent 3 **once** with the **same** input as the failed call; if it fails again, **exit** with error (**§ O2** below). | **Not implemented** in `run_wfm_registry_e2e`: there is **no** post–Agent 3 validation hook that detects “hard failure” and re-invokes Agent 3. | Add validation + **one** A3 retry before treating as hard failure. |

**E2E demo plan items** (curated pools **G6**, word cap **G7**, viewers **G8**, warm-registry **G9**): **planned and documented** in **`development_plan_wfm_registry_e2e_demo.md`**. Saying they are “not done” means **not implemented in the repo yet**, **not** that they are missing from the product plan.

**G3–G5 (handoff metadata):** **`wfm_orchestration/run_metadata.py`** — `new_bundle_id`, `wfm_pipeline_timestamps_at_accept`, `orchestration_run_id_accept`; wired in **`run_wfm_registry_e2e`**. CLI **`--bundle-id`** / **`--bundle-prefix`**.

---

## Normative references (behavior is fixed unless cited otherwise)

| Source | What it locks |
|--------|----------------|
| **`asp/wfm/Agent_WFM.md`** | Confirmation flow; **Style A** join for loop-back; **outer** full-WFM budget **1 initial + 3 reruns** (**4** total full passes) unless product changes; Agent 4 retry budget; **OUT_OF_SCOPE** require disagree+comment or **confirmed omit** before merge; **accept in full** → may proceed downstream **without** Agent 4. |
| **`pipeline_spec.md`** | WFM → registry **handoff** field meanings; per-line **`statement_nl`** as registry input lineage. |
| **`registry_persistence_v1.md`** | Bundle / line JSON shape consumed by **`registry_stage.loaders`**. |
| **`registry_stage/models.py`** | **`HandoffBundle`** / **`HandoffLine`** required fields and verdict set (`PASS` \| `REWRITE` \| `OUT_OF_SCOPE`). |

Orchestration **must not** invent alternate semantics; where **`Agent_WFM.md`** says *TBD* or *Open issues*, see **§ Open points** below.

---

## G1 — Acceptance → `HandoffBundle` → registry

### Intended behavior (from demo + product spec)

When the user **accepts** the confirmation package (or the **final** confirmation after any loop), the system **immediately** has enough **structured** state to build a valid **`HandoffBundle`** and call **`load_handoff_bundle`** / **`run_bundle_through_registry`** — **no** operator-authored JSON.

### Design (deterministic from spec + models)

1. **Hold in orchestration memory** (and optionally append to audit JSONL): per confirmation round — Agent 1–3 outputs, numbered package as shown to user, Agent 3 labels per index, user disagreements / omits / patches, merged Style-A string when applicable, **`wfm_compound_operator_limit`**, model id, timestamps.
2. **On “proceed to registry”** (accept in full on the **last** confirmation before downstream):
   - **`user_original_input`**: **first** user submission for this bundle (see **O3**, locked).
   - **`lines`**: one **`HandoffLine`** per **remaining** sub-statement row that **continues** in the bundle per **`Agent_WFM.md`** (after omits, **renumber** in UI; store **`line_index`** **0-based** in JSON to match **`registry_stage`** fixtures — **map** from 1-based confirmation indices explicitly).
   - **`statement_nl`** per line: **authoritative** text for that line as in the **confirmation package** (**PASS** = verbatim as shown; **REWRITE** = rewritten text as shown; **OUT_OF_SCOPE** = as shown with scope material — still present in handoff; registry **skips** in-scope processing per existing **`bundle_workflow`** rules).
   - **`agent3_verdict`**, **`scope_report`**, **`diff_report`**, **`agent2_line_text`**: copy from structured capture; **`None`** where optional.
   - **`confirmation_package_style_a`**: full joined package string when useful for audit (optional field).
   - **`bundle_id`**, **`wfm_pipeline_timestamps`**, **`orchestration_run_id`**, **`provider_model`**: set per **G3–G5** in the e2e plan (implementation defaults acceptable).
3. **Validate** with **`load_handoff_bundle`** before registry.

### What you do **not** need to decide if you accept the spec

- **Verdict enum** — fixed.
- **Skip OUT_OF_SCOPE lines in registry** — already **`bundle_workflow`** behavior.
- **Mapping 1-based UI → 0-based `line_index`** — single convention; document in code.

---

## G2 — Style-A merge → Agent 1 → 2 → 3 in one process

### Intended behavior

After programmatic **patch merge**, build **Style A** NL (**`Agent_WFM.md`** — numbered lines `1. …`, `\n` join). **Immediately** invoke **Agent 1** with **only** that string (no retry metadata). Then **Agent 2** → **Agent 3** → **confirmation** again, until user accepts or **outer** budget exhausts.

**After user agrees to Agent 4 output / patch (and merge is applied):** **no** separate **y/n** gate on merged text — the run **continues automatically** to **Agent 1** on the Style-A document. The UI **must** show plain-language text that this is happening (full WFM loop restarting). This matches demo intent: **(b)** speed, with **transparency** (not a silent jump).

### Design (deterministic from spec)

1. **Merge function** — implement **exactly** the Style-A rules in **`Agent_WFM.md`** (replacements, omits, renumber, join). Reuse or factor shared logic with any existing merge preview in **`test_sets/scripts/`** so preview and re-run **match**.
2. **Loop counter** — `full_wfm_passes_used` ≤ **4** (per **outer** budget in **`Agent_WFM.md`** line 265). **Do not** change without product edit to that doc.
3. **Agent 4** — when user disagrees, existing **Agent 4** contract ( **`WFM_PATCH`**, retries) applies **before** merge.
4. **After each full 1→2→3**, show **confirmation** again (same as today’s product expectation).

### What you do **not** need to decide if you accept the spec

- **Outer budget 4** — **locked** in **`Agent_WFM.md`** unless you explicitly change that file.
- **Agent 1 input on loop-back** — **only** merged NL string (no extra metadata).

---

## Resolved product / demo choices

| # | Topic | Resolution |
|---|--------|------------|
| **O1** | Optional **second confirmation** (y/n) on merged NL before Agent 1 re-run | **Resolved:** **No** extra confirmation step. After the user accepts Agent 4’s patch / merge result, the orchestrator **automatically** starts **Agent 1 → 2 → 3** on the Style-A merged text. **Required:** user-visible copy that **full WFM is re-running** from the top (not silent). This is **(b)** without silence, not **(a)**. |
| **O2** | Meaning of **“Agent 3 failed rewrite”** + recovery | **Clarified below** — **one** automatic retry with **identical** Agent 3 input; then exit with error if still failing. |
| **O3** | **`user_original_input`** when Style-A loops occurred | **Locked:** keep the **first** user submission in **`user_original_input`**; use **`confirmation_package_style_a`** / traces for merged text. |

### O2 — What “Agent 3 failed rewrite” refers to (not your normal REWRITE line)

Normal flow: Agent 3 labels each line **PASS**, **REWRITE** (with an in-scope rewritten sentence + diff), or **OUT_OF_SCOPE** (with scope justification; optional guidance). That all **succeeds** as model output and feeds the **confirmation package**.

**“Failed rewrite”** in **`Agent_WFM.md`** is a **rare hard-failure path**: Agent 3 **attempted** an in-scope rewrite that **does not** pass **system or policy checks** after the fact (e.g. output validation, safety gate, empty/malformed rewrite when one was required). This is **not** the normal **REWRITE** verdict with a valid package.

**Orchestration policy (resolved):**

1. **First failure** — **Immediately re-call Agent 3 once** with **exactly the same** input as the failed call (same Agent 2 decomposition text / same user message payload the first attempt used — **no** new prompt invention, **no** Agent 1/2 re-run between attempts).
2. **Second failure** — **Exit** the WFM run with a **clear, user-visible error** (same *class* as other WFM hard failures: user is notified and can revise input or retry later). **Do not** loop indefinitely.

**Triggers (v1):** keep **minimal** (e.g. unparseable or empty rewrite when REWRITE was required); **no** conflation with **OUT_OF_SCOPE** or normal **REWRITE**.

---

## Answer to “is everything decidable without the user?”

- **G1 / G2 behavior** remains anchored in **`Agent_WFM.md`** + registry contracts.
- **O1–O3** are **decided** as in the table above.
- **O2** retry-once-then-exit policy is **locked** as above; exact validation rules can stay **minimal** in v1.

No further **G1/G2-only** dev plan is **required** beyond this file — the e2e demo plan remains the umbrella; this document **specializes** G1/G2 only.
