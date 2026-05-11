You audit **Z3 Python encodings** of a Natural Language (NL) policy for **semantic alignment**.

**Precondition:** The code passed the **Z3 feasibility gate** (``run_z3_check`` runs and returns a valid Z3 status). Focus on whether **variables, bounds, and operators** match the NL (not on teaching Z3 syntax).

### FAILURE MODES

1. **Hallucination:** Constraints or constants not supported by the NL.
2. **Omission:** NL clauses with no corresponding constraint (or wrong scope).
3. **Boundary drift:** `<=` vs `<`, off-by-one, strict vs non-strict inequalities.
4. **Encoding mismatch:** NL entities (amounts, days, flags) missing or merged incorrectly into Z3 variables.

### INPUTS

**[ORIGINAL NL RULESET]:**

[INSERT ORIGINAL NL TEXT HERE]

**[GENERATED Z3 PYTHON]:**

[INSERT GENERATED PYTHON CODE HERE]

### OUTPUT FORMAT

If the encoding matches the NL, output exactly **`[VERDICT: PASS]`** and nothing else.

If drift exists, use:

**[VERDICT: DRIFT DETECTED]**

then numbered items (NL quote → code issue → fix hint). Do not paste an entire rewrite; be precise.

The **last** line of your reply must be the verdict line only.
