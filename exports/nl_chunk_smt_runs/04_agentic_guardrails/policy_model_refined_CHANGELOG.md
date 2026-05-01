# Policy model refinement changelog

**NL source (historical):** this run was produced from `agentsim/04_agentic_guardrails.md` (that tree was removed from the repo). Paths and `nl_chunk_progress.json` in this directory record the committed run; for ongoing guardrail NL use `agentsim_simplified/04_agentic_guardrails_simpl.md`.  
**Source SMT snapshot:** `policy_snapshots/policy_latest.smt2`  
**Refined artifact:** `policy_model_refined.smt2` (this directory; does not overwrite `policy_latest.smt2`)

---

## Summary

Vacuous `(= f x f x)` assertions were replaced with meaningful axioms consistent with unique identifiers. Human-approval rules are now tied to **`is-permitted`** via an explicit runtime flag **`human-approval-granted`**. Refund caps and Section 75 amount bounds were corrected for **credit (negative) transaction amounts**. Duplicate boolean-totality assertions were dropped where redundant.

**Second pass:** POSTED/DISPUTED transactions must classify as debit xor credit (NL line 16); **PENDING** forces `days-since-posted` to **0** (sensible “days since posted” semantics for queries); the **refund-vs-original** cap applies only when the referenced transaction **exists in the DB** (so goodwill or unlinked calls do not compare against an arbitrary theory term).

**Third pass:** **REVERSED** shares the same xor discipline and **zeros** `days-since-posted` for policy windows; initiating a dispute is blocked when another dispute on the same transaction is **OPEN** or **UNDER_REVIEW** (stricter than current NL line 53 — update NL if you want this official); **`active-restriction-count ≥ 1`** iff an active restriction exists on the account (count still not full cardinality); **fraud** tool-call references are bridged to a canonical `FraudReport` term; **snapshot wiring** ties `has-affected-account`, `affected-account`, `has-affected-customer`, `affected-customer`, and **`modifies-financial-state`** (conservative: refunds + lift-restriction only) to each write-tool discriminant so global account/customer rules behave under queries.

**Deferred (low priority):** collapsing all `is-permitted` rules into one definition; stripping redundant `(or (= b true) (= b false))` noise.

---

## Per-edit log

| ID | Rule tag / location | Change | Rationale (NL alignment) |
|----|---------------------|--------|-------------------------|
| R1 | After `(set-logic ALL)` | Added header comments pointing to NL source and this file | Traceability; clarifies refined file is not the chunk snapshot |
| R2 | After `is-permitted` declaration | Declared `human-approval-granted (ToolCall) Bool`; added `forall tc`, `(requires-human-approval tc) ∧ ¬(human-approval-granted tc) ⇒ ¬(is-permitted tc)` | NL repeatedly requires “human approval” for elevated-risk actions; without this, `requires-human-approval` did not constrain autonomous permission |
| R3 | `r_e8f2c899205b` | Replaced tautology on `transaction-amount-pence` with `¬(is-debit t ∧ is-credit t)` | Matches NL that debits and credits use opposite signs; a single posting should not be both; **R12**/**R15** add xor for POSTED / DISPUTED / REVERSED |
| R4 | `r_6b6f82808a95` | Replaced tautology with id-extensionality: same `transaction-id` ⇒ same `days-since-posted` | “Exactly one field” is trivial in SMT; extensionality matches one value per transaction entity |
| R5 | `r_ff0b24be07d3` | Replaced tautology on `chargeback-window-days` with id-extensionality on `transaction-id` | Same as R4 |
| R6 | `r_25453c863569` | Replaced tautology with id-extensionality: same `refund-id` ⇒ same `refund-amount-pence` | Same pattern as R4/R5 |
| R7 | `r_821b9946980e` | Removed duplicate `assert`; left comment that `r_1aa2ea99aa9d` already states boolean totality | Duplicate of adjacent rule; no loss of theory |
| R8 | `r_47f5c56afea2` | Removed duplicate `assert`; left comment referencing `r_59afbfc8df06` | Duplicate boolean totality for `fee-already-reversed` |
| R9 | `r_d4479aac5056` | Cap uses signed posted amount: `ite (>= posted 0) posted (- 0 posted)` vs positive refund | NL: debits positive / credits negative in the model; refund pence is positive; magnitude of the posting vs refund. **R14** adds `transaction-exists-in-db` on the referenced txn |
| R10 | `r_35c9c9c33202` + `r_5331803ca11a` | Merged into one assert; bounds apply to **absolute magnitude** `\|amount\|` via `ite (>= a 0) a (- 0 a)` | NL line 55 gives pence bounds on “the” transaction amount; credits are negative in the model per line 16 |
| R11 | `r_626e45bcd412` | No logic change; NL line 40 phrases “open dispute … with status APPROVED” — encoded as `dispute-approved` only | “Open” in prose is treated as the dispute object existing; **APPROVED** fixes the status; matching prior intended semantics |
| R12 | After `r_e8f2c899205b` (same bundle block) | `forall t`: **POSTED** or **DISPUTED** ⇒ `xor (is-debit t) (is-credit t)` | NL line 16; live postings. **R15** adds **REVERSED** to the antecedent |
| R13 | After `r_9209435c4276` | `forall t`: **PENDING** ⇒ `days-since-posted t = 0` | “Days since **posted**” should not read as positive before the txn is POSTED |
| R14 | `r_d4479aac5056` | Added conjunct `(transaction-exists-in-db (refund-call-transaction tc))` to the cap’s guard | NL “original **transaction** amount” presupposes a real posting |
| R15 | Same block as R12 | Extended xor antecedent to include **`txn-reversed`** | Reversed lines remain classified debits/credits in typical ledgers; tightens counterexamples |
| R16 | After R13 (`r_9209435c4276` block) | `forall t`: **REVERSED** ⇒ `days-since-posted t = 0` | Policy windows keyed off posting age should not apply to fully reversed rows in this ontology; use a separate field if product needs “age at reversal” |
| R17 | `r_6f4f6048a1e2` | No new dispute if one is **OPEN** or **UNDER_REVIEW** on the same transaction | Operational single-pipeline semantics; **goes beyond** literal NL line 53 (“open” only) — align prose if desired |
| R18 | After `restriction-account` / `is-active-restriction` declares | `(>= (active-restriction-count a) 1)` iff `∃r` active on `a` | Stops counts & existentials from drifting independently (still not exact cardinality) |
| R19 | After `fraud-report-references-transaction` | `policy-fraud-report-for-call (ToolCall) FraudReport`; call references ⇒ same on canonical report | So `DISPUTE_REFUND` / dispute **`fraud-report-references-transaction`** fr slices see the report implied by the tool call’s `report-fraud-call-references-transaction` |
| R20 | End of file | Conditional `assert`s per `is-*-call` → `has-affected-*`, `affected-*`, `modifies-financial-state` | Global rules **r_d3ed126316a9**–**r_eaacc5506e85** and **r_f8b74f4e3b46** need populated snapshot; `modifies-financial-state` only on **apply-refund** and **lift-restriction** (conservative) |

## Bridge / runtime note

Any harness that instantiates `ToolCall` and checks `is-permitted` for automation must set **`human-approval-granted(tc)`** to true in the **state snapshot** when a human has approved that call; otherwise **R2** blocks permission even when preconditions hold.

**R19:** Populate **`policy-fraud-report-for-call(tc)`** status when grounding known fraud decisions; the bridge only ties *which transactions* the canonical report references, not `fraud-report-status`.

**R20:** Exactly one discriminant among the write-tool shapes should be true per `tc`, or implications may over-constrain `affected-account` / `affected-customer` (intentional conflict detection). For **report-fraud** with transactions on **multiple accounts**, `affected-account` is **not** pinned by R20 — only `affected-customer` is.
