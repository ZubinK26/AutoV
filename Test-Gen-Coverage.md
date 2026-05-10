# Test-Gen-Coverage

Here is each proposed test type in simple terms, and the **question it helps answer**.

---

### 1. Scenario (world) template

**What it is:** A fixed snapshot of “what is true right now” (who, what, numbers, labels) that you feed into the policy machinery.

**Valuable question:** **“When the facts are exactly *this*, does the system still behave the same as before?”**

**Why it matters:** Catches accidental changes to how facts are read, compiled, or interpreted—not just wording changes in the NL.

---

### 2. Decision-query template

**What it is:** Those facts, plus one concrete “decision request” (e.g. “should this action go through?”).

**Valuable question:** **“For this situation, does the policy say *yes* / *no* / something else, exactly as we expect?”**

**Why it matters:** This is the core alignment check between **processed NL** and **executable policy**: same inputs → same decision.

---

### 3. Explanation / rule-attribution template

**What it is:** Same as (2), but the expected answer includes *which* rule (or pathway) is responsible, not only the final label.

**Valuable question:** **“Is the outcome right *for the right reason*, or only by accident?”**

**Why it matters:** Stops silent bugs where the model gives the correct yes/no but for the wrong rule or wrong precedence.

---

### 4. Boundary / monotonicity template

**What it is:** The same story, but you nudge one number (or ordered value) just below, on, and above a threshold.

**Valuable question:** **“Do comparisons and limits behave correctly *around the edge*—not only in the middle?”**

**Why it matters:** Most real-world policies hinge on “at least / at most / before / after”; this is where encoding errors show up first.

---

### 5. Counterfactual flip template

**What it is:** Two worlds that are almost identical except you change **one** fact; you expect the decision to change (or stay the same).

**Valuable question:** **“Does that *one* condition in the NL actually *control* the outcome the way it should?”**

**Why it matters:** Directly tests “if A then B” style logic without needing domain-specific vocabulary in the template.

---

### 6. Obligation / constraint inventory template

**What it is:** Instead of only approve/deny, you list what *must* hold (obligations, must-satisfy conditions) in a situation.

**Valuable question:** **“Are all the *attached requirements* present and correct, not just the headline decision?”**

**Why it matters:** NL often hides extra duties in the same sentence; this checks the **rich** meaning, not a single bit.

---

### 7. Sat / unsat / consistency template

**What it is:** You ask whether a set of facts can all be true at once under the policy (or whether they contradict).

**Valuable question:** **“Is the policy *internally consistent*, or does it secretly forbid impossible combinations?”**

**Why it matters:** Finds contradictions and dead logic that might never show up in a single happy-path query.

---

### 8. Pairwise equivalence / non-interference template

**What it is:** Two requests in the same world that should behave the same (or differently) because of one specific difference you name.

**Valuable question:** **“Should this attribute *matter* here—and does it, and *only* there?”**

**Why it matters:** Catches “spooky” interactions—unrelated fields changing the answer, or related fields being ignored.

---

### Quick map: “question → use this test”

| You care about… | Lean on… |
|-----------------|----------|
| Final yes/no vs golden | **Decision-query** |
| Stable inputs across versions | **Scenario** |
| Right rule / right precedence | **Rule-attribution** |
| Thresholds and edge cases | **Boundary / monotonicity** |
| “This clause actually drives the result” | **Counterfactual flip** |
| Extra conditions, not only allow/deny | **Obligation inventory** |
| Contradictions / impossible policies | **Sat / unsat** |
| Irrelevant fields staying irrelevant | **Equivalence / non-interference** |

---

## Proposed workflow (with the existing pivot pipeline)

This section answers: *given template-defined tests, how do we use them end-to-end, accounting for what the pipeline already does?*

**Same page on the core loop.** Yes: each template instance is **lowered** into queries against the **actual compiled policy model** (the same artifact the pipeline already treats as authoritative—e.g. Z3 after compile—not a paraphrase or a shadow model). You **run** those queries, collect **actual** results in a canonical form, **diff** against the stored **golden** for that instance, and obtain a **per-test verdict** (pass/fail/mismatch detail). That diff step is the behavioral alignment signal; what to do after a mismatch (repair, CI gate, snapshot updates) is **out of scope here and deferred**.

**What “Tester vs Critic vs templates” meant.** That was only about **dividing labor**, not about post-failure workflow:

- **Tester** and **Critic** use an LLM on NL + formal *excerpts* to flag broad narrative or structural drift (“does this still read like the same policy?”).
- **Template suite** uses the **model executor**: same inputs every time, comparable **actual vs golden**.

So: templates are not a replacement for Tester/Critic; they answer a different question (**executable behavior on pinned scenarios**). A plausible **order** in the pipeline is still: model compiled and checked → precheck → optional Tester → run template suite and record verdicts → Critic—simply because you need a real model before executable tests, and Tester/Critic are optional prose passes around that. **Order is not prescribing what you do when a template fails**; for now you stop at verdicts.

**Proposed stages (scope: through verdicts).**

1. **Template library (offline).** Define a small schema per template family (scenario fields, query shape, golden shape). No domain vocabulary is baked into the tooling—only types and enums.

2. **Fill / author instances.** An LLM (or human) produces *candidate* JSON rows from the active policy’s **effective NL** plus `meta_scheme.json` / pathway summary, or from `synthetic_en.md`. A **validator** rejects rows that are ill-typed, incomplete, or not lowerable (same spirit as extract schema repair).

3. **Deterministic lowering.** A pure function maps each validated instance to: facts/assertions, the query goal, and a **canonical golden** form (sorted obligation multiset, decision enum, sat bit, etc.). This uses the same IR / naming the compiler already emits so you do not invent a second semantics.

4. **Bind to a policy build (optional but useful).** Record which policy build the goldens belong with (e.g. artifact digest + semantics version) so reruns are interpretable.

5. **Run.** After the **real** policy model is available for this build, execute each lowered instance against it (reuse `run_z3_check`-style machinery or a thin query driver). Record **actual** in the same canonical form as golden.

6. **Diff and verdict.** Compare `actual` vs `golden` per instance; emit structured pass/fail (and diff detail). **Stop here for the current design intent**—remediation, gating, or refreshing goldens is deferred.

**Summary.** Templates are **filled** in the LLM-friendly layer, **validated**, **lowered** to the executable model, **run** on that model, **diffed** to goldens → **verdicts**. Tester and Critic remain separate, softer checks on prose alignment; they do not substitute for executable template results.
