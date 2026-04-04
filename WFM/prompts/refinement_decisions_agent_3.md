# Agent 3 prompt — issue status table

Tracks assessments and resolutions for [`agent_3_scope_rewrite.md`](agent_3_scope_rewrite.md). Last updated when that prompt was revised to match these rows.

| # | Issue | Status | Resolution |
|---|--------|--------|--------------|
| 1 | Input contract (provenance, order) | **Resolved** | Added **INPUT** block: sub-statements from **Agent 2**, process **every** line, **same order**. |
| 2 | “Every rewrite changes meaning” vs WFM | **Resolved** | Removed that assumption. Rewrites must be **equivalent in this context to the original** — not a different-but-related meaning; **minimize** change; diff notes substantive loss or **no substantive loss** when appropriate. Step-4 example is now an **equivalent** if-then rephrase; history/snapshot case called out as **counterexample** (use **OUT_OF_SCOPE** if equivalence cannot be defended). |
| 3 | Biconditional vs `pipeline_spec.md` | **Resolved** | IN SCOPE bullet for **biconditional / mutual implication**, with natural-language forms (**if and only if**, **iff**, **just when**, **exactly when**) plus two short examples. |
| 4 | Vague quantifiers (`most`, etc.) | **Resolved** | OUT OF SCOPE bullet for **ill-founded / vague quantifiers**, with **exception**: explicit **finite declared set** + **definable** condition (cardinality or precise fraction). Bare “most …” without sharpening stays out of scope. **Rationale:** see § below. |
| 5 | PASS paraphrase risk | **Resolved** | **PASS** must repeat the sub-statement **verbatim** (exact input line text). **OUT_OF_SCOPE** line also requires original **verbatim** for traceability. |
| 6 | Z3 / “triggers” exclusion from spec | **Open** | Not requested in this pass; still a possible future sync with `pipeline_spec.md` (“quantifier instantiation heuristics / triggers”). |
| 7 | Failed rewrite / validation (runtime) | **Resolved — no prompt change** | **What was meant:** `Agent_WFM.md` says **orchestration** may **reject** a REWRITE (validation/policy). Agent 3 does **not** see that verdict; it only emits text. A one-line prompt note was proposed only to stop the model from implying “final” or trying to simulate validation — **low value**, easy to confuse. **Decision:** omit from prompt; handle in implementation/docs. |

---

## Rationale: vague quantifiers vs finite sets and Z3

**Policy in the prompt:** Vague words like “most” are **out of scope** unless the user pins them to an **explicit finite** universe and a **sharp** condition (e.g. “strictly more than half of the elements of declared set S”).

**Why allow that exception?** Over a **finite** sort or finite subset S, many “fuzzy” notions become **ordinary cardinality constraints**: counts or fractions over a bounded domain. That is standard decidable FOL-style modeling over finite enumerations, not open-ended higher-order reasoning.

**Does Z3 allow it?** **Yes**, for finite domains: you can express properties like “more than half of S satisfies P” using counting or quantification over the finite sort (the exact encoding depends on how the formalizer models sets and cardinality). The hard part is not solver support for a **defined** threshold — it is **underdetermination** when the NL only says “most” with no rule for what counts. The exception **requires** that sharpening so the formalizer is not guessing.

**Why not allow bare “most” in scope?** Without a definable slice or fraction, different readers pick different thresholds; the rule is **not** uniquely formalizable — aligned with `pipeline_spec.md` excluding vague quantifiers unless made precise.
