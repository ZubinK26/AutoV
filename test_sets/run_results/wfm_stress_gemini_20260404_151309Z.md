# WFM automated run — stress harness (R-* / E-*), Agents 1 → 2 → 3, Gemini

**UTC timestamp:** 20260404_151309Z

## Contract (this run)

- **Example set:** `stress` (`test_sets/wfm_stress_examples_en.md`, ## STRESS)
- **Model:** `gemini-3.1-pro-preview`
- **Temperature:** `0.0`
- **Max output tokens:** `16384`
- **Thinking level:** `LOW` (see `GEMINI_THINKING_LEVEL`; default is `low` for parity with non–extended-thinking Claude runs)
- **Compound operator limit (injected):** `8`
- **Agent 4:** skipped (no user disagreement simulation)

Full table: `test_sets/wfm_api_contract_gemini.md`

---

## R-1 (reject · Agent 3 target — reporting-chain reachability)

### Input

Northwind Logistics assigns every field agent to exactly one regional lead, and every regional lead to exactly one operations director, and every operations director to exactly one vice president of logistics, and every vice president to the chief operating officer. Internal policy defines **reachability** in the reporting graph: an employee **can escalate to** another employee if there is a **finite chain** of direct reports (zero or more hops) from the first to the second. If an employee can escalate to the chief operating officer, then urgent capital requests from that employee are auto-approved up to the director level. Avery is a field agent. In conclusion: if Avery can escalate to the chief operating officer through the reporting chain, then Avery’s urgent capital requests are auto-approved up to the director level.

### Agent 1

Northwind Logistics assigns every field agent to exactly one regional lead, every regional lead to exactly one operations director, every operations director to exactly one vice president of logistics, and every vice president of logistics to the chief operating officer. Internal policy defines reachability in the reporting graph: an employee can escalate to another employee if there is a finite chain of direct reports (zero or more hops) from the first employee to the second employee. If an employee can escalate to the chief operating officer, then every urgent capital request from that employee is auto-approved up to the director level. Avery is a field agent. In conclusion: if Avery can escalate to the chief operating officer through the reporting chain, then every urgent capital request from Avery is auto-approved up to the director level.

### Agent 2

1. "Northwind Logistics assigns every field agent to exactly one regional lead."
2. "Northwind Logistics assigns every regional lead to exactly one operations director."
3. "Northwind Logistics assigns every operations director to exactly one vice president of logistics."
4. "Northwind Logistics assigns every vice president of logistics to the chief operating officer."
5. "Internal policy defines reachability in the reporting graph: an employee can escalate to another employee if there is a finite chain of direct reports (zero or more hops) from the first employee to the second employee."
6. "If an employee can escalate to the chief operating officer, then every urgent capital request from that employee is auto-approved up to the director level."
7. "Avery is a field agent."
8. "In conclusion: if Avery can escalate to the chief operating officer through the reporting chain, then every urgent capital request from Avery is auto-approved up to the director level."

### Agent 3

PASS: 1. "Northwind Logistics assigns every field agent to exactly one regional lead."
PASS: 2. "Northwind Logistics assigns every regional lead to exactly one operations director."
PASS: 3. "Northwind Logistics assigns every operations director to exactly one vice president of logistics."
PASS: 4. "Northwind Logistics assigns every vice president of logistics to the chief operating officer."
OUT_OF_SCOPE: 5. "Internal policy defines reachability in the reporting graph: an employee can escalate to another employee if there is a finite chain of direct reports (zero or more hops) from the first employee to the second employee." | REPORT: This rule requires computing a transitive closure (a chain of relationships of arbitrary length), which is out of scope. The system can only check direct relationships, not unbounded chains.
PASS: 6. "If an employee can escalate to the chief operating officer, then every urgent capital request from that employee is auto-approved up to the director level."
PASS: 7. "Avery is a field agent."
REWRITE: 8. "In conclusion: if Avery can escalate to the chief operating officer, then every urgent capital request from Avery is auto-approved up to the director level." | DIFF: Removed "through the reporting chain" to treat escalation as a direct property/relation rather than requiring the system to compute the recursive path.

---

## R-2 (reject · Agent 3 target quantifier — unbounded domain)

### Input

For **every natural number** slot index k with k at least 1, warehouse rack lane A-12 has a bin at position k whose labeled capacity in kilograms is **at least** twice the index k, and if the weight on hand in that bin ever exceeds the labeled capacity then the inventory system raises a critical alert for that bin. Lane A-12 currently has no bins with negative capacity labels. Bin 47 had a critical alert yesterday. If there is **any** natural number m such that bin m carries hazmat class 4 materials, then lane A-12 is on partial lockdown until the safety audit completes. In conclusion: lane A-12 is on partial lockdown until the safety audit completes.

### Agent 1

For every natural number slot index k where k is at least 1, warehouse rack lane A-12 has a bin at position k whose labeled capacity in kilograms is at least twice k, and if the weight on hand in the bin at position k ever exceeds the labeled capacity of the bin at position k, then the inventory system raises a critical alert for the bin at position k. Warehouse rack lane A-12 currently has no bins with negative capacity labels. The bin at position 47 had a critical alert yesterday. If there is any natural number m such that the bin at position m carries hazmat class 4 materials, then warehouse rack lane A-12 is on partial lockdown until the safety audit completes. In conclusion: warehouse rack lane A-12 is on partial lockdown until the safety audit completes.

### Agent 2

1. "For every natural number slot index k where k is at least 1, warehouse rack lane A-12 has a bin at position k whose labeled capacity in kilograms is at least twice k."
2. "For every natural number slot index k where k is at least 1, if the weight on hand in the bin at position k ever exceeds the labeled capacity of the bin at position k, then the inventory system raises a critical alert for the bin at position k."
3. "Warehouse rack lane A-12 currently has no bins with negative capacity labels."
4. "The bin at position 47 had a critical alert yesterday."
5. "If there is any natural number m such that the bin at position m carries hazmat class 4 materials, then warehouse rack lane A-12 is on partial lockdown until the safety audit completes."
6. "In conclusion: warehouse rack lane A-12 is on partial lockdown until the safety audit completes."

### Agent 3

OUT_OF_SCOPE: 1. "For every natural number slot index k where k is at least 1, warehouse rack lane A-12 has a bin at position k whose labeled capacity in kilograms is at least twice k." | REPORT: Unbounded domain (natural numbers) cannot be formalized.
OUT_OF_SCOPE: 2. "For every natural number slot index k where k is at least 1, if the weight on hand in the bin at position k ever exceeds the labeled capacity of the bin at position k, then the inventory system raises a critical alert for the bin at position k." | REPORT: Unbounded domain and temporal history ("ever exceeds") cannot be formalized.
PASS: 3. "Warehouse rack lane A-12 currently has no bins with negative capacity labels."
OUT_OF_SCOPE: 4. "The bin at position 47 had a critical alert yesterday." | REPORT: Temporal/state-history reasoning ("yesterday") cannot be formalized.
OUT_OF_SCOPE: 5. "If there is any natural number m such that the bin at position m carries hazmat class 4 materials, then warehouse rack lane A-12 is on partial lockdown until the safety audit completes." | REPORT: Unbounded domain ("any natural number") and temporal reasoning ("until") cannot be formalized.
OUT_OF_SCOPE: 6. "In conclusion: warehouse rack lane A-12 is on partial lockdown until the safety audit completes." | REPORT: Temporal reasoning ("until") cannot be formalized.

---

## R-3 (reject · Agent 3 target — vague quantifier over open class)

### Input

Most enterprise customers who upgraded to the premium analytics tier during the last two fiscal quarters also purchased the optional forecast pack, unless their procurement policy explicitly forbids add-on modules, and the finance team waived the add-on rule only for accounts flagged as strategic partnerships. **Most** self-serve retailers, however, stayed on the standard tier and never bought the forecast pack. If **most** active accounts in the EMEA region exceed their quarterly API call quota, then the platform enables throttling for all regional tenants until usage normalizes. Acme Trading is an EMEA retailer on the standard tier and has never purchased the forecast pack. In conclusion: Acme Trading is counted among the majority that stayed on the standard tier this year.

### Agent 1

Most enterprise customers who upgraded to the premium analytics tier during the last two fiscal quarters also purchased the optional forecast pack, unless the enterprise customer's procurement policy explicitly forbids add-on modules. The finance team waived the add-on rule only for accounts flagged as strategic partnerships. 

Most self-serve retailers stayed on the standard tier and never bought the forecast pack. 

If most active accounts in the EMEA region exceed the active account's quarterly API call quota, then the platform enables throttling for all EMEA regional tenants until usage normalizes. 

Acme Trading is an EMEA retailer on the standard tier and has never purchased the forecast pack. 

In conclusion: Acme Trading is counted among the majority that stayed on the standard tier this year.

### Agent 2

1. "Most enterprise customers who upgraded to the premium analytics tier during the last two fiscal quarters also purchased the optional forecast pack, unless the enterprise customer's procurement policy explicitly forbids add-on modules."
2. "The finance team waived the add-on rule only for accounts flagged as strategic partnerships."
3. "Most self-serve retailers stayed on the standard tier."
4. "Most self-serve retailers never bought the forecast pack."
5. "If most active accounts in the EMEA region exceed the active account's quarterly API call quota, then the platform enables throttling for all EMEA regional tenants until usage normalizes."
6. "Acme Trading is an EMEA retailer on the standard tier."
7. "Acme Trading has never purchased the forecast pack."
8. "In conclusion: Acme Trading is counted among the majority that stayed on the standard tier this year."

### Agent 3

OUT_OF_SCOPE: "Most enterprise customers who upgraded to the premium analytics tier during the last two fiscal quarters also purchased the optional forecast pack, unless the enterprise customer's procurement policy explicitly forbids add-on modules." | REPORT: The system cannot formalize the vague quantifier "most" without a precise numeric definition, nor can it evaluate historical timeframes like "during the last two fiscal quarters".
REWRITE: "If the finance team waived the add-on rule for an account, then the account is flagged as a strategic partnership." | DIFF: No substantive loss — rephrased "only for" into an explicit if-then implication.
OUT_OF_SCOPE: "Most self-serve retailers stayed on the standard tier." | REPORT: The system cannot formalize the vague quantifier "most" without a precise numeric definition.
OUT_OF_SCOPE: "Most self-serve retailers never bought the forecast pack." | REPORT: The system cannot formalize the vague quantifier "most" or historical state conditions like "never bought".
OUT_OF_SCOPE: "If most active accounts in the EMEA region exceed the active account's quarterly API call quota, then the platform enables throttling for all EMEA regional tenants until usage normalizes." | REPORT: The system cannot formalize the vague quantifier "most" or temporal conditions like "until usage normalizes".
PASS: "Acme Trading is an EMEA retailer on the standard tier."
OUT_OF_SCOPE: "Acme Trading has never purchased the forecast pack." | REPORT: The system cannot formalize historical state conditions like "never purchased".
OUT_OF_SCOPE: "In conclusion: Acme Trading is counted among the majority that stayed on the standard tier this year." | REPORT: The system cannot formalize vague concepts like "the majority" or temporal conditions like "this year".

---

## R-4 (reject · Agent 3 target — temporal / full history)

### Input

If an aircraft has **never** completed the required pitot-static verification since its last heavy maintenance, and it has accumulated at least seventy thousand flight hours since that maintenance, and at least three independent sensor drift events were logged for the same air data computer chain during the preceding twelve months, then the aircraft is grounded until both the air data system and the pitot-static checks pass with signed maintenance releases. Bluewing 441 has seventy-one thousand flight hours since its last heavy maintenance and four drift events logged in the last year, but maintenance records show only partial pitot-static checks, not the full verification package. In conclusion: Bluewing 441 is grounded until the air data system and pitot-static checks pass with signed releases.

### Agent 1

If an aircraft has never completed the required pitot-static verification since the aircraft's last heavy maintenance, and the aircraft has accumulated at least 70,000 flight hours since the aircraft's last heavy maintenance, and at least three independent sensor drift events were logged for the same air data computer chain of the aircraft during the preceding twelve months, then the aircraft is grounded until both the aircraft's air data system and the aircraft's pitot-static checks pass with signed maintenance releases. 

The aircraft Bluewing 441 has accumulated 71,000 flight hours since the aircraft Bluewing 441's last heavy maintenance, and four independent sensor drift events were logged for the same air data computer chain of the aircraft Bluewing 441 during the preceding twelve months, and the aircraft Bluewing 441 has never completed the required pitot-static verification since the aircraft Bluewing 441's last heavy maintenance. 

In conclusion: The aircraft Bluewing 441 is grounded until both the aircraft Bluewing 441's air data system and the aircraft Bluewing 441's pitot-static checks pass with signed maintenance releases.

### Agent 2

1. "If an aircraft has never completed the required pitot-static verification since the aircraft's last heavy maintenance, and the aircraft has accumulated at least 70,000 flight hours since the aircraft's last heavy maintenance, and at least three independent sensor drift events were logged for the same air data computer chain of the aircraft during the preceding twelve months, then the aircraft is grounded until the aircraft's air data system passes with signed maintenance releases."
2. "If an aircraft has never completed the required pitot-static verification since the aircraft's last heavy maintenance, and the aircraft has accumulated at least 70,000 flight hours since the aircraft's last heavy maintenance, and at least three independent sensor drift events were logged for the same air data computer chain of the aircraft during the preceding twelve months, then the aircraft is grounded until the aircraft's pitot-static checks pass with signed maintenance releases."
3. "The aircraft Bluewing 441 has accumulated 71,000 flight hours since the aircraft Bluewing 441's last heavy maintenance."
4. "Four independent sensor drift events were logged for the same air data computer chain of the aircraft Bluewing 441 during the preceding twelve months."
5. "The aircraft Bluewing 441 has never completed the required pitot-static verification since the aircraft Bluewing 441's last heavy maintenance."
6. "The aircraft Bluewing 441 is grounded until the aircraft Bluewing 441's air data system passes with signed maintenance releases."
7. "The aircraft Bluewing 441 is grounded until the aircraft Bluewing 441's pitot-static checks pass with signed maintenance releases."

### Agent 3

OUT_OF_SCOPE: 1. "If an aircraft has never completed the required pitot-static verification since the aircraft's last heavy maintenance, and the aircraft has accumulated at least 70,000 flight hours since the aircraft's last heavy maintenance, and at least three independent sensor drift events were logged for the same air data computer chain of the aircraft during the preceding twelve months, then the aircraft is grounded until the aircraft's air data system passes with signed maintenance releases." | REPORT: This rule requires temporal and state-history reasoning ("never completed since", "preceding twelve months", "until"), which the system cannot formalize.
OUT_OF_SCOPE: 2. "If an aircraft has never completed the required pitot-static verification since the aircraft's last heavy maintenance, and the aircraft has accumulated at least 70,000 flight hours since the aircraft's last heavy maintenance, and at least three independent sensor drift events were logged for the same air data computer chain of the aircraft during the preceding twelve months, then the aircraft is grounded until the aircraft's pitot-static checks pass with signed maintenance releases." | REPORT: This rule requires temporal and state-history reasoning ("never completed since", "preceding twelve months", "until"), which the system cannot formalize.
OUT_OF_SCOPE: 3. "The aircraft Bluewing 441 has accumulated 71,000 flight hours since the aircraft Bluewing 441's last heavy maintenance." | REPORT: This statement requires temporal reasoning ("since last heavy maintenance"), which is out of scope.
OUT_OF_SCOPE: 4. "Four independent sensor drift events were logged for the same air data computer chain of the aircraft Bluewing 441 during the preceding twelve months." | REPORT: This statement requires temporal reasoning ("during the preceding twelve months"), which is out of scope.
OUT_OF_SCOPE: 5. "The aircraft Bluewing 441 has never completed the required pitot-static verification since the aircraft Bluewing 441's last heavy maintenance." | REPORT: This statement requires temporal and state-history reasoning ("never completed since"), which is out of scope.
OUT_OF_SCOPE: 6. "The aircraft Bluewing 441 is grounded until the aircraft Bluewing 441's air data system passes with signed maintenance releases." | REPORT: This statement requires temporal reasoning about state transitions ("until"), which is out of scope.
OUT_OF_SCOPE: 7. "The aircraft Bluewing 441 is grounded until the aircraft Bluewing 441's pitot-static checks pass with signed maintenance releases." | REPORT: This statement requires temporal reasoning about state transitions ("until"), which is out of scope.

---

## R-5 (reject · Agent 3 target — higher-order / attribute quantification)

### Input

For **every criterion the procurement compliance board might adopt** when it evaluates a cloud vendor’s resilience story, if the vendor satisfies that criterion under the board’s published stress-test scenarios, then the vendor qualifies for the restricted federal data path, provided no subsidiary appears on the sanctions watchlist during the review window. Nimbus Cloud satisfies every criterion the board actually published in the April addendum, and no Nimbus subsidiary was listed during review. A subsidiary is **sanction-sensitive** if there is **some** future board meeting at which a new criterion could be introduced that the vendor would fail. If Nimbus is sanction-sensitive, the federal data path offer is void. In conclusion: Nimbus Cloud qualifies for the restricted federal data path and the offer is not void.

### Agent 1

For every criterion that the procurement compliance board might adopt when the board evaluates a cloud vendor’s resilience story, if the cloud vendor satisfies that criterion under the board’s published stress-test scenarios, and no subsidiary of the cloud vendor appears on the sanctions watchlist during the review window, then the cloud vendor qualifies for the restricted federal data path. 

Nimbus Cloud satisfies every criterion that the procurement compliance board actually published in the April addendum, and no subsidiary of Nimbus Cloud appeared on the sanctions watchlist during the review window. 

A cloud vendor is sanction-sensitive if there is some future board meeting at which a new criterion could be introduced that the cloud vendor would fail. 

If Nimbus Cloud is sanction-sensitive, then the restricted federal data path offer for Nimbus Cloud is void. 

In conclusion: Nimbus Cloud qualifies for the restricted federal data path, and the restricted federal data path offer for Nimbus Cloud is not void.

### Agent 2

1. "For every criterion that the procurement compliance board might adopt when the board evaluates a cloud vendor’s resilience story, if the cloud vendor satisfies that criterion under the board’s published stress-test scenarios, and no subsidiary of the cloud vendor appears on the sanctions watchlist during the review window, then the cloud vendor qualifies for the restricted federal data path."
2. "Nimbus Cloud satisfies every criterion that the procurement compliance board actually published in the April addendum."
3. "No subsidiary of Nimbus Cloud appeared on the sanctions watchlist during the review window."
4. "A cloud vendor is sanction-sensitive if there is some future board meeting at which a new criterion could be introduced that the cloud vendor would fail."
5. "If Nimbus Cloud is sanction-sensitive, then the restricted federal data path offer for Nimbus Cloud is void."
6. "In conclusion: Nimbus Cloud qualifies for the restricted federal data path."
7. "In conclusion: the restricted federal data path offer for Nimbus Cloud is not void."

### Agent 3

OUT_OF_SCOPE: "For every criterion that the procurement compliance board might adopt when the board evaluates a cloud vendor’s resilience story, if the cloud vendor satisfies that criterion under the board’s published stress-test scenarios, and no subsidiary of the cloud vendor appears on the sanctions watchlist during the review window, then the cloud vendor qualifies for the restricted federal data path." | REPORT: This rule quantifies over a hypothetical or computed set of criteria ("might adopt"), which requires higher-order or modal logic that is outside the system's scope.
OUT_OF_SCOPE: "Nimbus Cloud satisfies every criterion that the procurement compliance board actually published in the April addendum." | REPORT: This rule quantifies over a computed set ("every criterion that the board actually published"), which is outside the system's scope.
OUT_OF_SCOPE: "No subsidiary of Nimbus Cloud appeared on the sanctions watchlist during the review window." | REPORT: This rule requires temporal or state-history reasoning ("appeared... during the review window"), which is outside the system's scope.
OUT_OF_SCOPE: "A cloud vendor is sanction-sensitive if there is some future board meeting at which a new criterion could be introduced that the cloud vendor would fail." | REPORT: This rule requires reasoning about future events and hypothetical possibilities ("future board meeting", "could be introduced"), which is outside the system's scope.
PASS: "If Nimbus Cloud is sanction-sensitive, then the restricted federal data path offer for Nimbus Cloud is void."
PASS: "In conclusion: Nimbus Cloud qualifies for the restricted federal data path."
PASS: "In conclusion: the restricted federal data path offer for Nimbus Cloud is not void."

---

## R-6 (reject · Agent 2 target — dense compound operators in one rule stroke)

### Input

Every overseas supplier that ships temperature-sensitive biological reagents into at least one cold-chain port that serves at least three hospital networks **and** operates consolidation hubs in at least two countries **must** certify **every** inbound lot of **every** product family that crosses **any** of those cold-chain nodes, **and** must archive **every** temperature excursion log for **any** lot that either arrived more than six hours behind schedule **or** experienced a thaw-warning flag **or** was cleared only through an emergency deviation signed by **both** the importing site pharmacist **and** the carrier’s quality lead, **unless** the shipment was a dry-ice substitute protocol that the FDA letter explicitly exempts. Medalane Pharma is one such supplier, and lot L-903 crossed two cold-chain nodes last Tuesday with a thaw-warning flag but no dual-signed deviation. In conclusion: Medalane must archive the temperature excursion logs for lot L-903.

### Agent 1

Every overseas supplier that ships temperature-sensitive biological reagents into at least one cold-chain port that serves at least three hospital networks, and that operates consolidation hubs in at least two countries, must certify every inbound lot of every product family that crosses any of those cold-chain ports, and must archive every temperature excursion log for any lot that either arrived more than six hours behind schedule, experienced a thaw-warning flag, or was cleared only through an emergency deviation signed by both the importing site pharmacist and the carrier’s quality lead, unless the shipment of that lot was a dry-ice substitute protocol that the FDA letter explicitly exempts. 

Medalane Pharma is one such supplier, and lot L-903 crossed two cold-chain ports last Tuesday with a thaw-warning flag but without an emergency deviation signed by both the importing site pharmacist and the carrier's quality lead. 

In conclusion: Medalane Pharma must archive every temperature excursion log for lot L-903.

### Agent 2

LIMIT_EXCEEDED: true

OFFENDER: 1
SUBSTATEMENT_VERBATIM:
"Every overseas supplier that ships temperature-sensitive biological reagents into at least one cold-chain port that serves at least three hospital networks, and that operates consolidation hubs in at least two countries, must archive every temperature excursion log for any lot that arrived more than six hours behind schedule, unless the shipment of that lot was a dry-ice substitute protocol that the FDA letter explicitly exempts."
OPERATOR_TOTAL: 9
OPERATOR_BUDGET: 8
OPERATOR_TRACE:
- +1 quantifier: "Every" — 1
- +1 quantifier: "at least one" — 1
- +1 quantifier: "at least three" — 1
- +1 connective: "and" — 2
- +1 quantifier: "at least two" — 1
- +1 quantifier: "every" — 1
- +1 quantifier: "any" — 1
- +1 comparison: "more than" — 4
- +1 conditional_spine: "unless" — 3

SUMMARY:
The rule contains a highly complex subject restriction with multiple nested quantifiers that cannot be split without losing the meaning of the condition. Even after separating the disjunctive triggers for archiving logs, the baseline complexity of the supplier definition combined with the archiving requirement exceeds the operator budget.

### Agent 3

*SKIPPED — Agent 2 returned LIMIT_EXCEEDED (WFM would reset to user input).*

---

## E-1 (edge · Agent 2 — guard “If A and B then C” from invalid factorization)

### Input

Regional policy: **if** a borrower’s credit score is **below** six hundred **and** the borrower has **no** co-signer with a score **at least** seven hundred **and** the loan’s term exceeds **five** years, **then** the loan must be manually reviewed by an underwriter **and** cannot close automatically. River Bank approved an auto-closed mortgage for Dana, whose score is five eighty, with a six-year term and no qualifying co-signer. Every auto-closed mortgage that skips manual review violates Policy 14-B if the borrower lacks an exception code. Dana had no exception code. In conclusion: River Bank violated Policy 14-B on Dana’s loan.

### Agent 1

Regional policy: If a borrower’s credit score is below 600, and the borrower has no co-signer with a credit score of at least 700, and the loan’s term exceeds 5 years, then the loan must be manually reviewed by an underwriter and the loan must not close automatically. 

River Bank approved a mortgage for Dana that closed automatically, where Dana's credit score is 580, the mortgage has a 6-year term, and Dana has no co-signer with a credit score of at least 700. 

Every mortgage that closes automatically and is not manually reviewed by an underwriter violates Policy 14-B if the borrower lacks an exception code. 

Dana lacks an exception code. 

In conclusion: The mortgage approved by River Bank for Dana violates Policy 14-B.

### Agent 2

1. "If a borrower’s credit score is below 600, and the borrower has no co-signer with a credit score of at least 700, and the loan’s term exceeds 5 years, then the loan must be manually reviewed by an underwriter."
2. "If a borrower’s credit score is below 600, and the borrower has no co-signer with a credit score of at least 700, and the loan’s term exceeds 5 years, then the loan must not close automatically."
3. "River Bank approved a mortgage for Dana."
4. "The mortgage approved for Dana closed automatically."
5. "Dana's credit score is 580."
6. "The mortgage approved for Dana has a 6-year term."
7. "Dana has no co-signer with a credit score of at least 700."
8. "Every mortgage that closes automatically and is not manually reviewed by an underwriter violates Policy 14-B if the borrower lacks an exception code."
9. "Dana lacks an exception code."
10. "The mortgage approved by River Bank for Dana violates Policy 14-B."

### Agent 3

PASS: "If a borrower’s credit score is below 600, and the borrower has no co-signer with a credit score of at least 700, and the loan’s term exceeds 5 years, then the loan must be manually reviewed by an underwriter."
PASS: "If a borrower’s credit score is below 600, and the borrower has no co-signer with a credit score of at least 700, and the loan’s term exceeds 5 years, then the loan must not close automatically."
PASS: "River Bank approved a mortgage for Dana."
PASS: "The mortgage approved for Dana closed automatically."
PASS: "Dana's credit score is 580."
PASS: "The mortgage approved for Dana has a 6-year term."
PASS: "Dana has no co-signer with a credit score of at least 700."
PASS: "Every mortgage that closes automatically and is not manually reviewed by an underwriter violates Policy 14-B if the borrower lacks an exception code."
PASS: "Dana lacks an exception code."
PASS: "The mortgage approved by River Bank for Dana violates Policy 14-B."

---

## E-2 (edge · Agent 3 — open-ended symptom / “and similar complaints”)

### Input

Work-related asthma adjudication: documented symptoms include wheeze after shift change, chest tightness during cleaning with peracetic acid, exercise intolerance on stairs, morning cough, nocturnal awakenings with shortness of breath, peak-flow variability above twenty percent on home logs, and **similar respiratory complaints** not captured by the checklist. If two independent specialists document compatible findings **and** exposure history ties symptoms to the plant floor, the case is classified Tier-2 without appeal. Luis has two specialist reports and documented exposure; his file also notes **similar complaints** outside the checklist. In conclusion: Luis’s case is classified Tier-2 without appeal.

### Agent 1

Documented symptoms for work-related asthma adjudication include wheeze after a shift change, chest tightness during cleaning with peracetic acid, exercise intolerance on stairs, morning cough, nocturnal awakenings with shortness of breath, peak-flow variability above twenty percent on home logs, and similar respiratory complaints that are not captured by the checklist. 

If two independent specialists document compatible findings for a case and the exposure history ties the symptoms to the plant floor, then the case is classified as Tier-2 without appeal. 

Luis has two independent specialist reports documenting compatible findings, and an exposure history that ties his symptoms to the plant floor. Luis's file also notes similar respiratory complaints outside the checklist. 

In conclusion, Luis’s case is classified as Tier-2 without appeal.

### Agent 2

1. "Documented symptoms for work-related asthma adjudication include wheeze after a shift change."
2. "Documented symptoms for work-related asthma adjudication include chest tightness during cleaning with peracetic acid."
3. "Documented symptoms for work-related asthma adjudication include exercise intolerance on stairs."
4. "Documented symptoms for work-related asthma adjudication include morning cough."
5. "Documented symptoms for work-related asthma adjudication include nocturnal awakenings with shortness of breath."
6. "Documented symptoms for work-related asthma adjudication include peak-flow variability above twenty percent on home logs."
7. "Documented symptoms for work-related asthma adjudication include similar respiratory complaints that are not captured by the checklist."
8. "If two independent specialists document compatible findings for a case and the exposure history ties the symptoms to the plant floor, then the case is classified as Tier-2 without appeal."
9. "Luis has two independent specialist reports documenting compatible findings."
10. "Luis has an exposure history that ties his symptoms to the plant floor."
11. "Luis's file notes similar respiratory complaints outside the checklist."
12. "Luis’s case is classified as Tier-2 without appeal."

### Agent 3

PASS: 1. "Documented symptoms for work-related asthma adjudication include wheeze after a shift change."
PASS: 2. "Documented symptoms for work-related asthma adjudication include chest tightness during cleaning with peracetic acid."
PASS: 3. "Documented symptoms for work-related asthma adjudication include exercise intolerance on stairs."
PASS: 4. "Documented symptoms for work-related asthma adjudication include morning cough."
PASS: 5. "Documented symptoms for work-related asthma adjudication include nocturnal awakenings with shortness of breath."
PASS: 6. "Documented symptoms for work-related asthma adjudication include peak-flow variability above twenty percent on home logs."
PASS: 7. "Documented symptoms for work-related asthma adjudication include similar respiratory complaints that are not captured by the checklist."
PASS: 8. "If two independent specialists document compatible findings for a case and the exposure history ties the symptoms to the plant floor, then the case is classified as Tier-2 without appeal."
PASS: 9. "Luis has two independent specialist reports documenting compatible findings."
PASS: 10. "Luis has an exposure history that ties his symptoms to the plant floor."
PASS: 11. "Luis's file notes similar respiratory complaints outside the checklist."
PASS: 12. "Luis’s case is classified as Tier-2 without appeal."

---

## E-3 (edge · Agent 1 / 3 — grammatically incomplete disjunction)

### Input

Either the north approach lane’s concrete batch **or** the south approach lane’s batch for Runway 09/27. Every batch poured this week either passed slump testing **or** was re-threaded with additive, and the paving superintendent signs off only when both lane certificates are on file before the overnight cure window. The north lane batch was poured this week and did not receive additive; the south lane batch was poured this week, passed slump, and has the superintendent’s sign-off. If a runway batch fails slump and gets no additive, that runway end is closed to heavy jets until a new batch is certified. In conclusion: heavy jets may still use Runway 09/27 from the south end this week.

### Agent 1

There is a north approach lane concrete batch and a south approach lane concrete batch for Runway 09/27. Every concrete batch that was poured this week either passed slump testing or was re-threaded with additive. The paving superintendent signs off on a concrete batch only when both lane certificates are on file before the overnight cure window. The north approach lane concrete batch was poured this week and was not re-threaded with additive. The south approach lane concrete batch was poured this week, passed slump testing, and has the paving superintendent’s sign-off. If a runway concrete batch fails slump testing and is not re-threaded with additive, then that runway end is closed to heavy jets until a new concrete batch is certified. In conclusion: heavy jets may still use Runway 09/27 from the south end this week.

### Agent 2

1. "There is a north approach lane concrete batch for Runway 09/27."
2. "There is a south approach lane concrete batch for Runway 09/27."
3. "Every concrete batch that was poured this week either passed slump testing or was re-threaded with additive."
4. "The paving superintendent signs off on a concrete batch only when both lane certificates are on file before the overnight cure window."
5. "The north approach lane concrete batch was poured this week."
6. "The north approach lane concrete batch was not re-threaded with additive."
7. "The south approach lane concrete batch was poured this week."
8. "The south approach lane concrete batch passed slump testing."
9. "The south approach lane concrete batch has the paving superintendent’s sign-off."
10. "If a runway concrete batch fails slump testing and is not re-threaded with additive, then that runway end is closed to heavy jets until a new concrete batch is certified."
11. "In conclusion: heavy jets may still use Runway 09/27 from the south end this week."

### Agent 3

PASS: 1. "There is a north approach lane concrete batch for Runway 09/27."
PASS: 2. "There is a south approach lane concrete batch for Runway 09/27."
REWRITE: 3. "For every concrete batch, if the concrete batch was poured this week, then the concrete batch passed slump testing or was re-threaded with additive." | DIFF: No substantive loss — rephrased computed set ("that was poured this week") into an explicit if-then condition over the domain of concrete batches.
REWRITE: 4. "If the paving superintendent signs off on a concrete batch, then both lane certificates are on file before the overnight cure window." | DIFF: No substantive loss — rephrased "only when" into an explicit if-then statement.
PASS: 5. "The north approach lane concrete batch was poured this week."
PASS: 6. "The north approach lane concrete batch was not re-threaded with additive."
PASS: 7. "The south approach lane concrete batch was poured this week."
PASS: 8. "The south approach lane concrete batch passed slump testing."
PASS: 9. "The south approach lane concrete batch has the paving superintendent’s sign-off."
OUT_OF_SCOPE: 10. "If a runway concrete batch fails slump testing and is not re-threaded with additive, then that runway end is closed to heavy jets until a new concrete batch is certified." | REPORT: This rule involves temporal reasoning ("until a new concrete batch is certified"), which requires tracking state changes over time. The system can only evaluate static conditions.
REWRITE: 11. "Heavy jets may use Runway 09/27 from the south end this week." | DIFF: No substantive loss — removed the conversational transition "In conclusion:" to form a standard declarative property.

---

## E-4 (edge · Agent 2/3 — biconditional + bounded arithmetic chain)

### Input

Dock scheduling at Port Vale: a berth slot is **premium** if and only if the vessel’s declared LOA is **at most** two hundred forty meters **and** its arrival window fits entirely inside the morning tide gate, **or** the harbor master issues a paid priority token for that vessel. MV **Cornelia** declared two thirty-five meters, arrived inside the morning gate, and carries a priority token. Tonnage fees are waived **if and only if** the berth is premium **and** the carrier submits manifests **at least** forty-eight hours ahead **and** no hazardous class-1 cargo is declared. **Cornelia** filed manifests fifty hours early and declared only class-3 cargo. **If** tonnage fees are waived **then** the stevedore’s lift cap increases by **twenty** percent for that call. In conclusion: **Cornelia** receives the twenty-percent lift cap increase on this call.

### Agent 1

Dock scheduling at Port Vale: A berth slot assigned to a vessel is premium if and only if either the vessel’s declared LOA is at most 240 meters and the vessel's arrival window fits entirely inside the morning tide gate, or the harbor master issues a paid priority token for that vessel. MV Cornelia declared an LOA of 235 meters, has an arrival window that fits entirely inside the morning tide gate, and carries a paid priority token. Tonnage fees for a vessel's call are waived if and only if the vessel's berth slot is premium, the carrier submits manifests at least 48 hours ahead of arrival, and no hazardous class-1 cargo is declared for the vessel. MV Cornelia's carrier submitted manifests 50 hours ahead of arrival and declared only class-3 cargo. If tonnage fees for a vessel's call are waived, then the stevedore’s lift cap increases by 20 percent for that call. In conclusion: MV Cornelia receives the 20 percent stevedore's lift cap increase on this call.

### Agent 2

1. "A berth slot assigned to a vessel is premium if and only if either the vessel’s declared LOA is at most 240 meters and the vessel's arrival window fits entirely inside the morning tide gate, or the harbor master issues a paid priority token for that vessel."
2. "MV Cornelia declared an LOA of 235 meters."
3. "MV Cornelia has an arrival window that fits entirely inside the morning tide gate."
4. "MV Cornelia carries a paid priority token."
5. "Tonnage fees for a vessel's call are waived if and only if the vessel's berth slot is premium, the carrier submits manifests at least 48 hours ahead of arrival, and no hazardous class-1 cargo is declared for the vessel."
6. "MV Cornelia's carrier submitted manifests 50 hours ahead of arrival."
7. "MV Cornelia declared only class-3 cargo."
8. "If tonnage fees for a vessel's call are waived, then the stevedore’s lift cap increases by 20 percent for that call."
9. "MV Cornelia receives the 20 percent stevedore's lift cap increase on this call."

### Agent 3

PASS: 1. "A berth slot assigned to a vessel is premium if and only if either the vessel’s declared LOA is at most 240 meters and the vessel's arrival window fits entirely inside the morning tide gate, or the harbor master issues a paid priority token for that vessel."
PASS: 2. "MV Cornelia declared an LOA of 235 meters."
PASS: 3. "MV Cornelia has an arrival window that fits entirely inside the morning tide gate."
PASS: 4. "MV Cornelia carries a paid priority token."
PASS: 5. "Tonnage fees for a vessel's call are waived if and only if the vessel's berth slot is premium, the carrier submits manifests at least 48 hours ahead of arrival, and no hazardous class-1 cargo is declared for the vessel."
PASS: 6. "MV Cornelia's carrier submitted manifests 50 hours ahead of arrival."
PASS: 7. "MV Cornelia declared only class-3 cargo."
PASS: 8. "If tonnage fees for a vessel's call are waived, then the stevedore’s lift cap increases by 20 percent for that call."
PASS: 9. "MV Cornelia receives the 20 percent stevedore's lift cap increase on this call."

---

## E-5 (edge · Agent 2 — “Every X that is Y has Z” must stay one structured claim)

### Input

Every loan officer **that is** licensed in **both** California **and** Nevada **and** that has closed **at least** twelve rural-development deals in the **last** calendar year **has** an elevated approval ceiling of one-point-two million dollars for single-section manufactured housing, **unless** the borrower’s debt-to-income ratio **exceeds** forty-three percent **or** the census tract is flagged “infrastructure incomplete.” Jamie is licensed in both states, closed fifteen rural-development deals last year, but the subject tract is infrastructure-incomplete. The elevated ceiling **never** applies when the tract flag is set. In conclusion: Jamie may not use the elevated ceiling on this application.

### Agent 1

Every loan officer who is licensed in both California and Nevada and who has closed at least 12 rural-development deals in the last calendar year has an elevated approval ceiling of $1,200,000 for single-section manufactured housing, unless the borrower’s debt-to-income ratio exceeds 43% or the census tract is flagged "infrastructure incomplete". 

Jamie is a loan officer who is licensed in both California and Nevada, and Jamie has closed 15 rural-development deals in the last calendar year, but the subject census tract is flagged "infrastructure incomplete". 

The elevated approval ceiling never applies when the census tract is flagged "infrastructure incomplete". 

In conclusion: Jamie may not use the elevated approval ceiling on this application.

### Agent 2

1. "Every loan officer who is licensed in both California and Nevada and who has closed at least 12 rural-development deals in the last calendar year has an elevated approval ceiling of $1,200,000 for single-section manufactured housing, unless the borrower’s debt-to-income ratio exceeds 43% or the census tract is flagged "infrastructure incomplete"."
2. "Jamie is a loan officer who is licensed in both California and Nevada."
3. "Jamie has closed 15 rural-development deals in the last calendar year."
4. "The subject census tract is flagged "infrastructure incomplete"."
5. "The elevated approval ceiling never applies when the census tract is flagged "infrastructure incomplete"."
6. "Jamie may not use the elevated approval ceiling on this application."

### Agent 3

REWRITE: For every loan officer, if the loan officer is licensed in California and the loan officer is licensed in Nevada and the loan officer has closed at least 12 rural-development deals in the last calendar year, and it is not the case that the borrower's debt-to-income ratio exceeds 43% and it is not the case that the census tract is flagged "infrastructure incomplete", then the loan officer has an elevated approval ceiling of $1,200,000 for single-section manufactured housing. | DIFF: No substantive loss — rephrased computed set into explicit conditions and resolved "unless" into negated conditions.
REWRITE: Jamie is a loan officer and Jamie is licensed in California and Jamie is licensed in Nevada. | DIFF: No substantive loss — split compound property into explicit conjunction.
PASS: Jamie has closed 15 rural-development deals in the last calendar year.
PASS: The subject census tract is flagged "infrastructure incomplete".
REWRITE: If the census tract is flagged "infrastructure incomplete", then the elevated approval ceiling does not apply. | DIFF: No substantive loss — rephrased "never applies when" into explicit if-then.
PASS: Jamie may not use the elevated approval ceiling on this application.

---

## E-6 (edge · Agent 3 — nested conditional chain; should remain in-scope per prompt)

### Input

If a book is **more than** twenty-one days overdue **and** the borrower **is** a library member, **then** **if** the accrued fine **exceeds** the member’s fine cap **and** the member has **not** enrolled in the amnesty weekend, the member is **suspended** from borrowing **and** the account is flagged for desk review; **if** the member **has** enrolled in the amnesty weekend, **then** **instead** only the suspension applies until the book is returned **and** the fine is paid down to zero. Riley’s book is twenty-four days overdue, Riley is a member, the fine exceeds Riley’s cap, Riley did **not** enroll in amnesty, and the book is **not** yet returned. In conclusion: Riley’s account is flagged for desk review.

### Agent 1

If a book is **more than** twenty-one days overdue **and** the borrower of the book **is** a library member, **then** **if** the accrued fine for the book **exceeds** the member’s fine cap **and** the member has **not** enrolled in the amnesty weekend, the member is **suspended** from borrowing **and** the member's account is flagged for desk review; **if** the member **has** enrolled in the amnesty weekend, **then** **instead** only the suspension applies until the book is returned **and** the accrued fine is paid down to zero. The book borrowed by Riley is twenty-four days overdue, Riley is a library member, the accrued fine for the book exceeds Riley’s fine cap, Riley did **not** enroll in the amnesty weekend, and the book borrowed by Riley is **not** yet returned. In conclusion: Riley’s account is flagged for desk review.

### Agent 2

1. "If a book is more than twenty-one days overdue and the borrower of the book is a library member and the accrued fine for the book exceeds the member’s fine cap and the member has not enrolled in the amnesty weekend, then the member is suspended from borrowing."
2. "If a book is more than twenty-one days overdue and the borrower of the book is a library member and the accrued fine for the book exceeds the member’s fine cap and the member has not enrolled in the amnesty weekend, then the member's account is flagged for desk review."
3. "If a book is more than twenty-one days overdue and the borrower of the book is a library member and the accrued fine for the book exceeds the member’s fine cap and the member has enrolled in the amnesty weekend, then the member is suspended from borrowing until the book is returned and the accrued fine is paid down to zero."
4. "The book borrowed by Riley is twenty-four days overdue."
5. "Riley is a library member."
6. "The accrued fine for the book exceeds Riley’s fine cap."
7. "Riley did not enroll in the amnesty weekend."
8. "The book borrowed by Riley is not yet returned."
9. "Riley’s account is flagged for desk review."

### Agent 3

PASS: 1. "If a book is more than twenty-one days overdue and the borrower of the book is a library member and the accrued fine for the book exceeds the member’s fine cap and the member has not enrolled in the amnesty weekend, then the member is suspended from borrowing."
PASS: 2. "If a book is more than twenty-one days overdue and the borrower of the book is a library member and the accrued fine for the book exceeds the member’s fine cap and the member has not enrolled in the amnesty weekend, then the member's account is flagged for desk review."
OUT_OF_SCOPE: 3. "If a book is more than twenty-one days overdue and the borrower of the book is a library member and the accrued fine for the book exceeds the member’s fine cap and the member has enrolled in the amnesty weekend, then the member is suspended from borrowing until the book is returned and the accrued fine is paid down to zero." | REPORT: The use of "until" introduces temporal and state-history reasoning, which the system cannot formalize.
PASS: 4. "The book borrowed by Riley is twenty-four days overdue."
PASS: 5. "Riley is a library member."
PASS: 6. "The accrued fine for the book exceeds Riley’s fine cap."
PASS: 7. "Riley did not enroll in the amnesty weekend."
PASS: 8. "The book borrowed by Riley is not yet returned."
PASS: 9. "Riley’s account is flagged for desk review."

---
