# Dev plan — Full ClinCon fragment: theory-aware grounding & solving (`&sum` / clingcon)

**Status:** **Implemented** in `asp_pipeline/clingcon_api.py`, `clingo_check.py`, `policy_check.py` (see git history on `ClinCon-version` after 2026-04-26). Optional: re-run the nl chunk `pending_asp` case to confirm end-to-end.  
**Align [`asp_pipeline`](../asp/asp_pipeline/)** with the **normative** ClinCon-safe fragment in [`asp/pipeline_wfm_to_asp.md`](../asp/pipeline_wfm_to_asp.md) §2.1 (notably “Bounded integer arithmetic via ClinCon constraint variables” and `&sum{...}`), and with prompts that tell the LLM to use that syntax.

**Post-implementation validation (explicit):** Re-run the NL chunk flow that previously failed with **`PARSE_GROUND_FAIL`** / `theory atom: sum/0` (same handoff / `pending_asp` path under [`wfm_orchestration/nl_chunk_policy_pipeline.py`](../wfm_orchestration/nl_chunk_policy_pipeline.py)) and confirm **parse+ground** (and, where applicable, **policy_check**) succeed for the same bundle.

---

## 1. Problem statement

| Layer | What we have today | What the docs / prompts say |
|--------|---------------------|-----------------------------|
| **Spec** | [`asp/pipeline_wfm_to_asp.md`](../asp/pipeline_wfm_to_asp.md) §2.1 | ✅ `&sum{...}` in scope; line 143 says ClinCon constraint syntax is used for numeric constraints. |
| **WFM** | [`WFM/prompts/agent_3_scope_rewrite.md`](../WFM/prompts/agent_3_scope_rewrite.md) | “Linear integer constraints (ClinCon-style sums, …)”. |
| **Formalizer** | [`asp_pipeline/prompts/formalizer_new.md`](../asp_pipeline/prompts/formalizer_new.md) | Instructs `&sum{...}`-style for integers (line 17). |
| **Oracle** | [`asp_pipeline/clingo_check.py`](../asp_pipeline/clingo_check.py) | `Control().add(...); .ground()` and/or **`clingo --ground`** on a temp file — **no** registered **constraint theory**. |

**Symptom:** Grounding fails with e.g. `no definition found for theory atom: sum/0` / `grounding stopped because of errors` when the model emits `&sum{...}` (the failure mode you already saw in bundle logs). That is **not** an LLM “inventing” a forbidden feature relative to the written spec — it is **implementation lag** behind the written ClinCon fragment.

**Terminology (implementation):** Potassco’s **clingcon** (PyPI: `clingcon`) is the standard way to support **`&sum`** (and related constraint constructs) in Clingo 5. Project prose uses **“ClinCon”**; the code change targets **clingcon** integration (plus any other theories you later add — out of scope for this milestone unless listed in §2.1).

---

## 2. Goals

1. **Parse + ground check** in `clingo_check` accepts the **full** §2.1 fragment that uses **`&sum{...}`** (and any other **clingcon**-covered syntax you explicitly keep in the spec for this release).
2. **Same dependency story** in CI, dev machines, and docs: version-pinned `clingo` + `clingcon` (and matching wheels where available).
3. **`policy_check` / solve path** can run on accumulated `policy_model.lp` that may contain those constructs (today [`policy_check.py`](../asp_pipeline/policy_check.py) uses `Control()` without theory — same gap).
4. **Regression:** Existing bundles that use **only** core ASP (no `&...` theory atoms) still pass checks **or** a documented **single** code path is used for all programs to avoid split-brain.

5. **Validation run:** After merge, re-run the **same** user scenario that hit **PARSE_GROUND_FAIL** on the nl chunk handoff; expect **at least** successful **grounding** (critic / commit may still fail for unrelated reasons — separate triage).

---

## 3. Non-goals (this milestone)

- **New** NL or WFM semantics; only tooling alignment.
- **Guaranteeing** the LLM always emits **well-formed** `&sum` (repair loop still applies); we only **enable** the checker to evaluate what the spec allows.
- **Other** theories (e.g. custom propagators) unless already listed in §2.1 with clear syntax — if needed, a **separate** follow-up plan.
- **Performance tuning** beyond reasonable timeouts (reuse existing `ASP_PIPELINE_CLINGO_*_TIMEOUT` or extend if grounding with clingcon is slower — measure in spike).

---

## 4. Technical spike (mandatory, before large refactors)

**Objective:** Prove end-to-end that **grounding** (and, if required for a sound “has a model” check, **solving** with `prepare` + `on_model`) works with **clingcon** for programs matching §2.1 examples.

1. **Install** `clingcon` in a venv next to the pinned `clingo` version (see Potassco compatibility notes; align with e.g. `clingo>=5.7` already referenced in [`test_sets/requirements-wfm-test.txt`](../test_sets/requirements-wfm-test.txt) or the project’s main requirements file when you centralize).

2. **Reproduce** the official pattern from Potassco docs: `Control`, `ProgramBuilder`, `parse_string`, **clingcon** `Theory.register`, `rewrite_ast` on the AST, then `ground`, then `theory.prepare`, then `solve` as needed. **Note:** Plain `ctl.add("base", [], program_string)` is **insufficient** for clingcon; the spike must use the **AST rewrite** path the theory expects.

3. **Clarify** whether **`clingo` subprocess** (`clingo --ground file.lp`) can ground **the same** programs without a Python-side theory (often **no** for `&sum`). Outcome: either document **“ground check = Python+clingcon only”** for theory programs, or find a **supported CLI** (e.g. a `clingcon` or `clingo` mode) and wrap it — **one** supported approach only, clearly documented.

4. **Windows:** Confirm wheels or build steps for the team’s main OS; if fragile, document WSL or conda fallback in [`asp/pipeline_wfm_to_asp.md`](../asp/pipeline_wfm_to_asp.md) install section.

**Exit criterion:** A minimal `.lp` from §2.1 using `&sum` **grounds** (and, if the spike shows solve is required to validate sat, **solves**) under the chosen approach, plus a second fixture **without** `&` that still passes on the same path (or a documented **fast** path for theory-free programs).

---

## 5. Design outline

### 5.1 `clingo_check.py`

- **Detection:** If combined `existing + proposed` contains **theory** syntax your fragment allows (e.g. regex for `&sum` or a broader `&[a-z]` after `#` or line-start as appropriate — **tighten** to avoid false positives), route to the **clingcon** path; else optionally keep the current fast `subprocess` + `add()` path, **or** use one unified path for fewer branches (spike will recommend).

- **Clingcon path:** Build program via `parse_string` + `ProgramBuilder` + `Theory('clingcon', …).rewrite_ast` + `ground` + `prepare`; for **“does it ground?”** define whether `ground` alone is enough or a **zero**-or **one-model** `solve` is required (copy Potassco examples).

- **Timeouts / errors:** Map clingcon/Clingo exceptions into the same `(ok, stage, detail)` shape as today so [`pipeline.py`](../asp_pipeline/pipeline.py) and logs do not need structural changes.

- **Parse-only:** Either unchanged for theory-free blocks, or use the same **parser** that clingcon rewrites (spike) so parse failures are consistent.

### 5.2 `policy_check.py`

- Revisit embedded `Control().add` path: policies with `&sum` will **not** work until **clingcon** (or the same unified helper) is used for **load + ground + solve**.

- **Subprocess** branch: if you keep `clingo` on the file, **verify** it supports the committed policy language; if not, **force** the Python+clingcon path when theory is present or always.

### 5.3 Config / env

- New optional env, e.g. `ASP_PIPELINE_CLINGCON=1` (default **on** after cutover) or `ASP_PIPELINE_USE_CLINGCON=1`, plus optional **disable** for debugging core-only programs.
- Document **`pip install clingo clingcon`** (or exact pins) in [`asp/pipeline_wfm_to_asp.md`](../asp/pipeline_wfm_to_asp.md) and [`.env.example`](../.env.example) if present.

### 5.4 Documentation

- In [`asp/pipeline_wfm_to_asp.md`](../asp/pipeline_wfm_to_asp.md) §4 (or a new “Tooling / oracle” subsection): state that **theory atoms in §2.1** require the **clingcon** integration; the **plain** `clingo` CLI **without** that stack may **not** be sufficient for `&sum`.
- In [`dev_plans/dev_plan_implementation_clincon_asp_v1.md`](dev_plan_implementation_clincon_asp_v1.md): add a **pointer** to this plan and mark the prior “Clingo vs ClinCon feature gap” item as **addressed** when this ships.

**Prompts:** No **mandatory** change if they already match §2.1; optional: one line that “grounding in CI uses **clingcon** for `&sum`” to reduce model confusion. **Do not** strip `&sum` from prompts — that would contradict the full scope you are enabling.

---

## 6. Work breakdown (checklist)

| # | Task | Notes |
|---|------|--------|
| S1 | **Spike** (§4) — document decision: subprocess vs Python-only, exact API sequence | Artifacts: short `docs/` or `dev_plans/` spike note is optional |
| S2 | Add **dependencies**: pin `clingcon` (+ doc compatibility with `clingo`) in the project’s main dependency file | Same versions in CI |
| S3 | Implement **clingcon grounding** helper(s); unit tests with **minimal** `&sum` and **theory-free** program | See [`asp_pipeline/tests/`](../asp_pipeline/tests/) |
| S4 | Wire **check_parse_and_ground** (and `check_ground` / `check_parse_only` if needed) to use helper when theory in scope | Preserve failure categories |
| S5 | Update **policy_check** for policies containing theory | Re-run or add integration test |
| S6 | **Docs** + env + README install one-liner | |
| S7 | **Full test suite** for `asp_pipeline` + any NL chunk / integration test you normally run | |
| S8 | **User validation run:** re-run the failing **nl chunk** case (`nl_ruleset_input` / `nlchunk_20260426_170115Z_d6c1e903` or current `pending_asp` bundle) | Log `PARSE_GROUND_FAIL` → expect pass on ground stage; save bundle path in PR notes |

---

## 7. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| **clingcon** not available on some platforms | Document pins; WSL/conda; optional feature flag to fall back to core-ASP-only **only** for dev emergency (not for production if spec says full fragment). |
| **AST** path slower / more fragile | Cache decision from spike; keep theory-free fast path if measurably worth it. |
| **LLM** still emits **malformed** `&sum` | Unchanged: repair cap + better feedback from **full** clingo/clingcon stderr in logs (optional small improvement: surface stderr in `check_detail` beyond “grounding stopped because of errors”). |
| **Two code paths** drift | Prefer one **unified** clingcon-aware path if perf allows (spike). |

---

## 8. Success criteria (sign-off)

- [ ] Unit tests: **at least one** `&sum` program from §2.1 **grounds** (and solve path validated per spike) via `asp_pipeline` checks.  
- [ ] Regression: **theory-free** program still **passes** (or same path).  
- [ ] `policy_check` can handle a small policy with **`&sum`** committed.  
- [ ] Docs and dependencies updated; **ClinCon vs plain Clingo** no longer a silent gap.  
- [ ] **Re-run** the nl chunk scenario that **failed** parse/ground; **grounding stage succeeds** (document bundle id and log snippet).

---

## 9. References

- Product spec: [`asp/pipeline_wfm_to_asp.md`](../asp/pipeline_wfm_to_asp.md) §2.1, §4, line 143.  
- Current oracle: [`asp_pipeline/clingo_check.py`](../asp_pipeline/clingo_check.py).  
- Policy solve: [`asp_pipeline/policy_check.py`](../asp_pipeline/policy_check.py).  
- Potassco: [clingo `Theory` + clingcon](https://potassco.org/clingo/python-api/5.5/clingo/theory.html) (example with `&sum` and `clingcon`).  
- Original pivot plan: [`dev_plans/dev_plan_implementation_clincon_asp_v1.md`](dev_plan_implementation_clincon_asp_v1.md) (B1 clingo check — to be superseded in behavior by this plan for theory programs).

When this plan is **approved for implementation**, create a short-lived **implementation branch** and track tasks through §6; **after** merge, run §8 user validation and attach results to the PR or release note.
