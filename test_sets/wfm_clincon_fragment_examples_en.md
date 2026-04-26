# WFM — ClinCon-safe fragment smoke examples (Agents 1–3)

**Purpose:** Small English blocks to exercise **Agent 3** after the **ClinCon / ASP** scope pivot. These are **not** a full benchmark; use with `run_wfm_folio_gemini.py` / `run_wfm_folio_claude.py` via `--examples` (see **`test_sets/README.md`**).

**Expectations:** Outcomes depend on the model; the **intended** Agent 3 labels are noted in comments. Re-run and refresh baselines when changing prompts.

**Layout:** Same as stress file: `### C-n` cases under `## CLINCON`.

---

## CLINCON

### C-1 (in-scope · finite domain + default exception)

Season is one of spring, summer, autumn, or winter. Promotion pricing applies in every season unless the account is on the sanctions watchlist. Acme Corp is not on the watchlist. In conclusion: promotion pricing applies to Acme Corp in winter.

### C-2 (in-scope · temporal fluent over finite steps)

Time steps are integers from 0 through 48 inclusive. Gate G7 is either open or closed at each step and cannot be both. If gate G7 is open at step T and no close command occurs at T, then gate G7 stays open at step T+1. At step 0 gate G7 is open. No close command occurs at any step from 0 through 47. In conclusion: gate G7 is open at step 48.

### C-3 (in-scope · bounded choice)

For each pawn P that reaches the last rank, exactly one promotion choice applies among queen, rook, bishop, and knight. Pawn p12 reached the last rank. In conclusion: pawn p12 is promoted to exactly one of queen, rook, bishop, or knight.

### C-4 (out-of-scope · nonlinear)

For every listed SKU, the clearance price is the square of the shelf age in days plus a fixed markdown, and if the clearance price exceeds the regional cap then the SKU cannot be sold. SKU K9 has shelf age 6 days. In conclusion: SKU K9 may or may not be sold depending on the cap.

### C-5 (out-of-scope · unbounded naturals)

For every natural number n strictly greater than zero, warehouse lane L has a bin at index n whose labeled capacity is at least n kilograms. In conclusion: lane L has infinitely many bins.

### C-6 (out-of-scope · vague quantifier)

Most active tenants in building B reported HVAC faults last quarter. If most tenants reported faults, the landlord must hire an independent engineer. In conclusion: the landlord must hire an independent engineer.
