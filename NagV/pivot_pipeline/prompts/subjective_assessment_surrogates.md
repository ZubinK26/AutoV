# Subjective assessment surrogates (in scope — no invented metrics)

Qualitative norms (“clear,” “well-written,” “professional,” “badly structured,” “similar technology”) are **encodable** without turning them into fake 0–100 scores or unstated numeric cutoffs.

**Value model:** The policy states **what must hold** (bool or finite set). **Document assessment** (extract + provenance + external-case tiers) supplies values — not hallucinated proficiency metrics.

## When to use (S1–S4)

| ID | English cue | Rewrite / IR direction | Do **not** |
|----|-------------|------------------------|------------|
| **S1** | Ability / clarity / quality (“can write clear technical English,” “communicates clearly”) | One **bool** surrogate per obligation, name like `candidate_can_write_technical_english` or `assignment_repository_well_structured`; NL: “… must be **true** (assessed from document evidence).” Extract: **`CONSTANT_RELATIONAL`** `EQ true` or global obligation on that bool. | Invent `proficiency_score`, `quality_rating`, or “must be **> 90**” unless the **source states a number**. |
| **S2** | Penalty / points **only when source gives a number** (“10 point penalty if …”) | Keep the **stated int**; use **`SUM_THRESHOLD`** / **`ARITHMETIC_EVALUATION`** / int vars as appropriate. | Replace a qualitative penalty with a bool only, or invent point totals not in source. |
| **S3** | “One of [A,B,C] or similar / equivalent” | **Finite list** in NL → **`K_OF_N`** / **`SET_INCLUSION`** / *at least one of: …*; optional separate bool `has_similar_technology` only if NL explicitly allows equivalence beyond the list — disclose in `semantic_deltas`. | Collapse list to one vague category; invent numeric similarity score. |
| **S4** | Comparative without metric (“best candidate,” “most relevant”) | Prefer **bool** threshold surrogate (“meets_relevance_bar”) or finite enum; disclose judgment in `semantic_deltas`. | **Scalarize** into 0–100 or rank scores not in source. |

## Naming (bool surrogates)

- Use **descriptive snake_case** that states the **judgment being assessed**, not a fake instrument: `candidate_can_write_technical_english`, `repository_is_well_structured`.
- Avoid names implying hidden metrics: not `english_proficiency_score`, `structure_quality_index`.

## Extract / WFM

- **Default:** qualitative “must / shall / required to” without numeric spec → **bool** + **`CONSTANT_RELATIONAL`** or **`LOGICAL_IMPLICATION`** on that bool (global obligation when policy applies to all subjects in scope).
- **`INT_RANGE` / `SUM_THRESHOLD`:** only when the **source line** states quantities, weights, or point values.
- Tag scope lines: **`subjective_assessment`** (see scope rewriter taxonomy).

## External case (downstream)

Bool surrogates are **grounded** variables: phase-1 fill may set `present` / `inferred` from document judgment with line cites; tier-1 strict requires provenance; tier-3 may suggest values only for **missing** pathway vars — same pipeline as today.
