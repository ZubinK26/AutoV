# Registry persistence v1

**Status:** Accepted — concrete JSON shapes for implementers. Canonical product intent remains **`pipeline_spec.md`**. If this file conflicts with `pipeline_spec.md`, **`pipeline_spec.md`** wins until this file is updated.

**Locks (no further product decisions required for v1):**

- **`line_index`:** **0-based** within the bundle (first line is `0`).
- **ID prefixes:** `sort_`, `ent_`, `fn_` (immutable, never reused; retired entries use **tombstone** below).
- **`committed_edges`:** **Embedded on each rule row** (no separate writable edge table in v1).

---

## 1. Top-level files

| File | Role |
|------|------|
| `registry.json` | All registry entries + optional global `entry_edges` (D3). |
| `rules.json` | All committed rule rows. |
| `bundles/{bundle_id}.json` | Immutable WFM→registry **handoff** (schema = *WFM → registry handoff* in `pipeline_spec.md`). |
| `bundles/{bundle_id}.pipeline.json` | Mutable pipeline state for that bundle. |

Each JSON file SHOULD include `"schema_version": "registry_persistence_v1"` at the top level (or inside a `meta` object if you already use one).

---

## 2. `relationship` enum v1

Closed set for **`committed_edges[].relationship`** (and for draft/debug tools if mirrored).

| Value | Meaning |
|--------|---------|
| `CREATED_BY_RULE` | This registry entry was **introduced** (first materialized) for this rule on this **commit**. |
| `MENTIONED_IN_NL` | Linked from WFM / resolve text for this line (tokens ↔ known symbols); deterministic linking only. |
| `APPEARS_IN_FOL` | Entry is referenced in the **accepted** formal artifact (FOL / AST walk / normalized IDs). |
| `LOADED_FOR_VALIDATION` | Entry was part of the **theory fragment** loaded for the Z3 check for this rule (includes supporting axioms/sorts if your builder adds them). |

**Rules:** `CREATED_BY_RULE` MUST NOT be reused for an entry that already existed before this rule’s commit (reuse → use the other labels). Add new enum values only in a **v2** with `schema_version` bump and migration notes.

---

## 3. `pipeline_status` (bundle sidecar)

Used in **`bundles/{bundle_id}.pipeline.json`**.

| Value | Meaning |
|--------|---------|
| `pending` | Handoff saved; pipeline not finished or user has not committed. |
| `committed` | User approved; all intended in-scope lines for this bundle were committed together. |
| `partially_committed` | User approved committing **only** a subset; see `committed_line_indices` / `committed_rule_ids`. |
| `failed` | Run ended without production commit (or user **abandoned**); see optional `failure_summary`. |

---

## 4. Registry entry (one object in `registry.json`)

**`kind`** discriminates optional fields. Unused keys SHOULD be omitted (not `null` noise), except where noted.

### Example — sort

```json
{
  "id": "sort_003",
  "kind": "sort",
  "name": "Animal",
  "members": ["ent_010", "ent_011"],
  "source_rule": ["rule_042"],
  "nl_description": "Named animals in the domain.",
  "status": "active",
  "embedding": [0.01, -0.02]
}
```

### Example — constant

```json
{
  "id": "ent_010",
  "kind": "constant",
  "name": "fluffy",
  "parent_sort_id": "sort_003",
  "source_rule": ["rule_042"],
  "nl_description": "Example pet cat.",
  "status": "active",
  "embedding": [0.03, 0.04]
}
```

### Example — function (predicate = codomain sort bool)

```json
{
  "id": "fn_012",
  "kind": "function",
  "name": "is_mammal",
  "domain_sort_ids": ["sort_003"],
  "codomain_sort_id": "sort_bool",
  "source_rule": ["rule_042"],
  "nl_description": "True when the animal is a mammal.",
  "status": "active",
  "embedding": [0.05, 0.06]
}
```

**Key reference**

| Key | Applies to | Required when |
|-----|------------|----------------|
| `id` | all | always |
| `kind` | all | always — `sort` \| `constant` \| `function` |
| `name` | all | always |
| `members` | `sort` | if enumerated; else `[]` or omit per policy |
| `parent_sort_id` | `constant` | always |
| `domain_sort_ids` | `function` | always (arity = length) |
| `codomain_sort_id` | `function` | always (`sort_bool` for predicates) |
| `source_rule` | all | list of `rule_id` strings (**authoritative** provenance; update on each linking commit) |
| `nl_description` | all | always (may be `""` only if truly unavoidable) |
| `embedding` | all | **recommended** for search; MAY omit if stored in a sidecar / rebuilt on load |
| `status` | all | `active` \| `tombstoned` |
| `tombstone_reason` | all | optional string when `status` is `tombstoned` |

`registry.json` shell:

```json
{
  "schema_version": "registry_persistence_v1",
  "entries": [],
  "entry_edges": []
}
```

**`entry_edges`:** optional list for **D3** non-derived links, e.g. `{ "from_id", "to_id", "relationship" }` with relationship strings **local** to entry–entry (not the same enum as rule–entry unless you intentionally unify later). Empty `[]` in v1 is fine.

---

## 5. Rule row (one object in `rules.json`)

```json
{
  "schema_version": "registry_persistence_v1",
  "rules": [
    {
      "rule_id": "rule_042",
      "bundle_id": "bundle_7f3a",
      "line_index": 0,
      "statement_nl": "Every cat is a mammal.",
      "z3_python_source": "# z3 code or heredoc string",
      "committed_edges": [
        { "entry_id": "fn_020", "relationship": "CREATED_BY_RULE" },
        { "entry_id": "sort_003", "relationship": "APPEARS_IN_FOL" }
      ],
      "wfm_pipeline_timestamps": {
        "confirmation_accepted_utc": "2026-04-04T12:00:00Z",
        "rule_committed_utc": "2026-04-04T12:05:00Z"
      },
      "orchestration_run_id": "orr_20260404_abc123"
    }
  ]
}
```

**`committed_edges` row:** exactly **`entry_id`** + **`relationship`** (enum §2). **`rule_id`** is implicit from the parent object.

**Formal code:** `z3_python_source` MAY be replaced by `formal_artifact_ref` (path) later if blobs grow large — pick one per deployment and stay consistent.

---

## 6. Bundle pipeline sidecar (one file)

`bundles/bundle_7f3a.pipeline.json`:

```json
{
  "schema_version": "registry_persistence_v1",
  "bundle_id": "bundle_7f3a",
  "pipeline_status": "committed",
  "orchestration_run_id": "orr_20260404_abc123",
  "updated_at": "2026-04-04T12:05:01Z",
  "committed_rule_ids": ["rule_042", "rule_043"],
  "committed_line_indices": [0, 1],
  "failure_summary": null
}
```

For **`partially_committed`**, `committed_*` lists reflect **only** shipped lines; uncommitted lines stay in **`bundles/{bundle_id}.json`** for a **new** bundle retry per `pipeline_spec.md`.

---

## 7. Validation reminders (~ `validate_alignment`)

On commit, tooling SHOULD assert (policy from `pipeline_spec.md`):

- For every `{ "entry_id", "relationship" }` in `committed_edges`, **`entry_id`** exists and `entries[].source_rule` contains **`rule_id`** (membership policy).
- `CREATED_BY_RULE` only when the entry first appeared on that commit (implementation enforces).

---

## 8. What to design next: registry vs workflow

**Executable milestones:** **`development_plan_registry_stage_v1.md`** (M0–M6, pre–formalizer).

**Do both in one thin vertical slice**, in this order:

1. **Persistence v1** (this doc) + load/save helpers + `validate_alignment` stub.
2. **Registry workflow** (search → resolve → populate) **against** these keys, with **in-memory** draft until commit — aligns with *Failure / commit contract*.

Pure **workflow-first** without frozen keys invites rename churn; pure **registry-first** without a scripted “happy path” risks over-modeling.

**Vertical slice:** one handoff → one line → search (empty registry → create entries) → resolve → user confirmation → session populate. **Full product slice** then adds mock or real formalizer → Z3 → critic → **production commit** → `rules.json` + `registry.json` + `bundles/*.pipeline.json` per *Failure / commit contract*.

---

## 9. Phase 1 scope (pre–formalizer — agreed)

Goals that **stop before** the formalizer (`pipeline_spec.md` step 4) still **fully use step 3** (Registry agent): search → gap extraction → resolve (substitution / side-by-side) → user agree or disagree → **populate in session** as context for the next stage.

| In scope for Phase 1 | Out of scope (later) |
|----------------------|----------------------|
| Session registry + resolved NL + traceability keyed by `bundle_id` / `line_index` | Production **`rules.json`** rows |
| Thin load/save helpers and optional session export aligned with this schema | **`committed_edges`** on persisted rules |
| Mapping session outputs to keys in this doc for a smooth formalizer phase | Production **rule commit** and **`validate_alignment`** on full graph (until end-to-end exists) |

**Note:** Phase 1 does **not** relax product rules for **production** files — it defers writing them until the full accept path (or uses **dev-only** exports). `registry_persistence_v1` still **defines** future fields so session data does not need a breaking rename.

---

## 10. Implementation gaps — resolution status

| Item | Status | Notes |
|------|--------|-------|
| **WFM ↔ orchestrator input (dev / simulation)** | **Resolved** | After user acceptance, treat **structured handoff** as the boundary: **fixtures**, **in-process** calls, **`bundles/{bundle_id}.json`**. Enough to implement and **try** the registry stage without a network API. |
| **WFM ↔ orchestrator (production)** | **Follow-up when needed** | Live **event/API** shape remains **TBD** (`WFM/Agent_WFM.md` — open issues). Does **not** block Phase 1 if the resolved boundary above is enough for your build. |
| **Playground vs production persistence** | **Resolved (nuanced)** | **Phase 1 / learning:** in-memory session and optional **dev exports** — not asserted as **production commit**. **Production:** **`registry.json`** / **`rules.json`** mutate per *Failure / commit contract* (typically after formalizer + checks in the full product). |
| **Registry workflow (steps and behavior)** | **Resolved** | **`pipeline_spec.md` step 3**; no further architecture gate for “what happens before formalizer.” |
| **Registry agent LLM prompts** | **To do when needed** | Author when you implement the LLM-backed registry step; not spelled out in `pipeline_spec.md`. |
| **Repository layout / packaging** | **Resolved (M0–M1)** | Python package **`registry_stage/`** (load handoff / registry, dev `export_session`, `validate_alignment` stub); **`bundles/`** at repo root; see **`registry_stage/README.md`**. |
| **CI strategy (live LLM vs fixtures)** | **To do when needed** | Decide when registry code has automated tests. |
