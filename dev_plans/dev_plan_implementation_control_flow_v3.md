# Implementation plan — NL→SMT-LIB pipeline (`control_flow_v3.md`)

## Purpose

Implement **`control_flow_v3.md`** as the **new** v1 product path: **SMT-LIB** as canonical artifact, **single** `policy_model.smt2`, **no separate registry**, **formalizer + syntax (Z3 parse) + semantic critic + atomic commit**. This document is the engineering plan; **`control_flow_v3.md`** remains the normative spec.

---

## Delta vs current codebase (AutoV today)

| Area | Current (v1 NL→Z3 + registry) | Target (v3) |
|------|--------------------------------|-------------|
| Stored logic | Per-line Z3 **Python**; optional `bundle_merge` | **SMT-LIB** only; one append-only file |
| “Registry” | `registry_stage`, `RegistrySession`, embeddings | **None** — policy file **is** the model |
| Agents | Formalizer + registry agent + validation gate | **Formalizer** + **critic** (no registry agent) |
| Repair | Formalizer/registry repair caps | **Loop 1** syntax (parse), **Loop 2** semantic (critic); budgets per spec |
| Commit | Per-line partial commit possible | **Whole-bundle** commit or fail; **no** partial commit |
| IDs | Mixed (`rule_*` UUIDs in nl_z3) | **`bundle_id` + `rule_id`** — see § Resolved decisions |
| Artifacts | `result.json`, optional `bundle_merge.json` | `policy_model.smt2`, `bundles/{bundle_id}.json`, `bundles/{bundle_id}.log.jsonl` |

**Implication:** v3 is largely a **new vertical slice** (new package or renamed pipeline). **Deprecate or freeze** `nl_z3_pipeline` + `registry_stage` **for this product path** unless you explicitly keep dual tracks.

---

## Milestones

### M0 — Spec lock + repo layout

- [x] **Title:** `control_flow_v3.md` H1 aligned to “(v3)” (was “v1”).
- [ ] Create package directory **`smt_pipeline/`** at repo root (see § Resolved decisions).
- [ ] **Missing** `policy_model.smt2` = empty policy (0 rules). **No** stub file required until first successful commit.
- [ ] Implement per § Resolved decisions (IDs, parse, corrupt file, context limit).

### M1 — Rule counting + bundle record shell

- [ ] Implement **regex-based** scan of `policy_model.smt2` for Rule headers (`control_flow_v3.md` § Rule counting). Unit tests on fixture snippets.
- [ ] **Size cap pre-check:** if `current_rule_count + in_scope_lines > 50` → fail `SIZE_CAP_REACHED` before LLM calls.
- [ ] **ID generation:** orchestration generates `bundle_id` and ordered `rule_id`s per IN_SCOPE line after cap passes; **no recycling** on failure (spec § ID policy).
- [ ] Write **`bundles/{bundle_id}.json`** skeleton (accepted_at, rule_ids, out_of_scope indices, wfm_payload, pipeline_status).

### M2 — Formalizer + in-memory block

- [ ] **Formalizer LLM** call: inputs = WFM slice + **full** `policy_model.smt2` (or `""`), **rule_ids** per line; output = **SMT-LIB block** with **normative** comment headers (`Bundle`, `Rule`, `NL`).
- [ ] Prompts TBD per spec § “Deferred: prompts” — track as **blocking** sub-deliverable.

### M3 — Loop 1: Syntax check (Z3 parse)

- [ ] Concatenate `existing_content + "\n\n" + new_block` **in memory only**.
- [ ] Run **Z3** (or Z3’s SMT-LIB front-end) **parser** on full string; capture parse errors. **No** file write until commit.
- [ ] **Loop 1:** budget 3; feedback = parse error + new block to formalizer.
- [ ] Map failures to **`SYNTAX_FAIL`** when budget exhausted.

**Parser:** See § Resolved decisions — in-process Z3 parse + timeout.

### M4 — Loop 2: Semantic critic

- [ ] **Critic LLM** with structured JSON output (`approved`, `objections[]`) per spec.
- [ ] **Loop 2:** budget 3; feedback = objections to formalizer.
- [ ] On each critic-accepted candidate revision: **re-parse once** (counts against Loop 2 budget on failure); **no** re-entry to Loop 1 from inside Loop 2 (spec).
- [ ] Map to **`SEMANTIC_FAIL`** when budget exhausted.

### M5 — Atomic commit + logging

- [ ] **Commit:** write `policy_model.smt2.new`, rename to `policy_model.smt2` (same dir).
- [ ] Update `bundles/{bundle_id}.json` (`committed_at`, `pipeline_status: committed`).
- [ ] **Append-only** `bundles/{bundle_id}.log.jsonl` per iteration (syntax + semantic loops).

### M6 — CLI + harness

- [ ] CLI entry: `--handoff` (WFM bundle JSON), `--policy-model` path (default `./policy_model.smt2`), `--out-bundle-dir` (default `./bundles/`).
- [ ] End-to-end test: empty file → one bundle → file grows; second bundle append; cap rejection test.

### M7 — (Optional) Deprecation / coexistence

- [ ] Document whether `nl_z3_pipeline` remains supported for experiments or is **archived**; avoid two conflicting “truth” pipelines without a clear product flag.

---

## Resolved engineering decisions (lock-in)

These satisfy **`control_flow_v3.md`** intent: same control flow, failure categories, artifacts, and append-only semantics. Where we add a **new** failure name, it is **stricter** than the spec minimum (does not weaken guarantees).

### 1. Syntax check — Z3 API + timeout

| Decision | **In-process** parse using Z3’s Python API (`parse_smt2_string` / equivalent shipped with the project `z3` dependency) on the **full in-memory concatenation**. |
|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Timeout** | Bounded wall-clock (default **30s**, env e.g. `SMT_PIPELINE_PARSE_TIMEOUT_SEC`). On timeout → treat as parse **failure** for that iteration (Loop 1 or the one-shot parse inside Loop 2). |
| **Why not subprocess `z3`** | Fewer moving parts; error string still passed to formalizer. Subprocess remains an allowed **fallback** if in-process API differs by platform (document in code only if needed). |

**Functionality vs spec:** **Unchanged.** Spec requires parse pass/fail + error feedback; delivery mechanism is an implementation detail.

---

### 2. ID format — UUID-style (no shared counter file)

| Decision | **`bundle_id`:** `b_` + first **16 hex chars** of a **uuid4** (no dashes), e.g. `b_a1b2c3d4e5f67890`. **`rule_id`:** `r_` + **12 hex chars** uuid4 per rule, globally unique, assigned **in `line_index` order** after cap check. |
|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Handoff** | If WFM already provides `bundle_id`, **use it** (must be non-empty). If absent, CLI generates. **Rule IDs** generated by pipeline in order when not pre-supplied. |
| **Why not `b_0001`** | Avoids a **counter file** and concurrent-writer races; spec only requires **global uniqueness** and immutability. |

**Functionality vs spec:** **Unchanged** for IDs (unique, stable, pre-assigned). **Trade-off:** human ordering by id string is weaker than monotonic counters; **audit** still uses `committed_at` + bundle headers in the file. Counters can be added later without breaking the format.

---

### 3. Missing vs corrupt `policy_model.smt2`

| State | Behavior |
|-------|----------|
| **Missing** | Treat as **0** rules; formalizer gets `""`; first commit creates the file. **Matches spec § Empty policy model.** |
| **Empty file** | Same as missing (0 rules). |
| **Non-empty but parse fails** (whole-file parse at pipeline start) | **Fail closed:** do not run formalizer. Failure category **`POLICY_MODEL_CORRUPT`** with `detail` in bundle record. **No auto-truncate.** |
| **Recovery** | Operator replaces file from backup or deletes to start fresh (documented). |

**Functionality vs spec:** **Stricter** than hoping the file is valid; preserves append-only **intent**.

---

### 4. Formalizer + critic context limits

| Decision | Pass **full** `policy_model.smt2` and full WFM payload as in spec **until** a single measured input exceeds the configured model window. Then **fail** with **`CONTEXT_LIMIT_EXCEEDED`** in bundle record. **No silent truncation.** |

**Functionality vs spec:** **Aligns** with “no truncation at 50 rules.” **Adds** one explicit failure mode the spec did not name; behavior is **safer** than truncating.

---

### 5. Where IDs are minted

| Decision | **`smt_pipeline` CLI** generates `bundle_id` (if absent) and all **`rule_id`**s for the run. **WFM** integration may supply `bundle_id`; **single process** per commit. |
|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Concurrency** | v1: **one writer** to `policy_model.smt2`. Multi-process concurrent commits **undefined** (document). |

**Functionality vs spec:** **Matches** orchestration-owned ids.

---

### 6. Critic, whole-bundle failure, bundle merge

| Topic | Decision |
|-------|----------|
| **Critic** | No extra programmatic gates beyond spec. |
| **Whole-bundle failure** | **As spec** — no partial commit. |
| **`nl_z3` / `bundle_merge`** | **Not** part of v3. |

**Functionality vs spec:** **Unchanged.**

---

### 7. Prompts

| Decision | **Stub files** `smt_pipeline/prompts/formalizer_v3.md`, `critic_v3.md` with required sections; full prose iterated in product. Pipeline **requires** files to exist. |

**Functionality vs spec:** State machine **complete**; NL/SMT quality **depends** on prompt content.

---

## Testing matrix (minimum)

| Case | Expected |
|------|----------|
| Empty policy file, first bundle | Commit creates file; Rule headers parse |
| Second bundle append | Single file contains two bundle blocks |
| Parse error | Loop 1 retries; then SYNTAX_FAIL |
| Critic rejects | Loop 2 retries; then SEMANTIC_FAIL |
| 49 rules in file, bundle has 2 IN_SCOPE lines | SIZE_CAP_REACHED before formalizer |
| OUT_OF_SCOPE lines | No rule_id; listed in bundle JSON |
| Corrupt existing policy file | `POLICY_MODEL_CORRUPT`, no formalizer run |
| Prompt + policy file exceed context budget | `CONTEXT_LIMIT_EXCEEDED` (or equivalent in `failure_reason`) |

---

## Out of scope for this dev plan (explicit)

- Registry embeddings, semantic search, `registry_stage` features
- Contradiction detection, graph edges
- `control_flow_v1.md` per-line isolated Z3 semantics (different product)
- **Final** formalizer/critic prompt prose — **stubs** required per §7; quality iteration is ongoing

---

## Summary

Implement **`smt_pipeline/`** per milestones M0–M6 using **§ Resolved engineering decisions**. **`control_flow_v3.md`** behavior (loops, caps, artifacts, atomic commit, no registry) is **fully covered**; additions (**`POLICY_MODEL_CORRUPT`**, **`CONTEXT_LIMIT_EXCEEDED`**) only **tighten** failure handling. The legacy **Z3 Python + registry + bundle merge** stack remains a **separate track** unless product explicitly maintains both.
