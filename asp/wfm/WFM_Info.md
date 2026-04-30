Agent Module Information

Agent 1 

Ambiguity Types \- 

**Confirmed from datasets — full ambiguity list:**

1. **Scope ambiguity** — "big and dangerous animals" (big-and-dangerous? or big, and also dangerous?)  
2. **Attachment ambiguity** — "in the zone or the area unless trained" (does "unless" attach to both or just the last?)  
3. **Pronoun/coreference ambiguity** — "if it is X" (what is "it"?)  
4. **Quantifier scope ambiguity** — "every team has a leader" (one leader total, or one per team?)  
5. **Negation scope** — "not all A are B" vs "all A are not B"  
6. **Conjunction/disjunction scope** — "A and B or C" — (A∧B)∨C or A∧(B∨C)?  
7. **Conditional attachment** — "if A then B and C" — if→(B∧C) or (if→B)∧C?  
8. **Plural/collective vs distributive** — "the teams have a leader" — one shared or one each?  
9. **Implicit quantification** — "dogs are mammals" — all dogs? Generic statement?  
10. **Comparative ambiguity** — "A is bigger than B and C" — bigger than both? Or bigger than B, and C exists?  
11. **Adjective-noun scope** — "old men and women" — old men \+ women, or old men \+ old women? (This is the FOLIO "brave and a man" pattern)  
12. **Ellipsis** — "John likes chess and Mary football" — does Mary like football, or does Mary play football?

**Summary of actionable numbers:**

* **Compound operator limit:** 8 per atomic statement (see `asp/wfm/config/wfm.json`)  
* **Ambiguity types to check:** 12 (listed above)  
* **Primary benchmarks:** FOLIO, P-FOLIO, ProofWriter OWA-5  
* **Secondary benchmarks:** LogicBench (FOL portion), PC-FOL, LogicNLI  
* **Stress test:** FOL-Pretrain (for volume/complexity edge cases)

Agent 2 \-

**Compound operator limit: 8.** Lower per-premise counts are common, but full FOLIO-style **single-sentence** casings (e.g. exclusive-or / neither-nor bundles) can need more headroom without safe splitting. The budget is still finite: anything above the configured limit should trigger **LIMIT_EXCEEDED** with a structured operator trace (Agent 2 prompt) for the user.
