# WFM stress harness — edge cases and reject cases (Agents 1–3)

**Purpose:** Automated runs (same choreography as FOLIO / P-FOLIO) with **medium–hard**-sized blocks. A case is **acceptable** if the pipeline **stops safely by the Agent 3 outcome** (inclusive of **Agent 2 `LIMIT_EXCEEDED`** or **Agent 3 `OUT_OF_SCOPE`**), or **passes with honest REWRITE** for edge items — **which agent** catches it is not scored here.

**ClinCon-version note:** Agent 3 scope was originally aligned with **many-sorted FOL / SMT** (e.g. “no recursion”, “no temporal”). Under the **ClinCon-safe ASP** fragment (**`docs/pipeline_wfm_to_asp.md` §2**), some cases here (e.g. finite-domain chains, finite-step fluents) may warrant **re-baselining** — use **`wfm_clincon_fragment_examples_en.md`** (`--clincon`) for smoke against the new prompt.

**Layout:** `### R-n` = **reject** (intended out-of-band for fully in-scope formalization per `agent_3_scope_rewrite.md` or too dense for Agent 2’s compound-operator budget). `### E-n` = **edge** (boundary / stress; may **PASS**, **REWRITE**, or legitimately **OUT_OF_SCOPE** depending on model).

**Run:** `python test_sets/scripts/run_wfm_folio_gemini.py --stress` (or `--examples` pointing here with stress mode per script). **Do not** mix this section into `wfm_folio_pffolio_examples_en.md`; this file is standalone.

---

## STRESS

### R-1 (reject · Agent 3 target — reporting-chain reachability)

Northwind Logistics assigns every field agent to exactly one regional lead, and every regional lead to exactly one operations director, and every operations director to exactly one vice president of logistics, and every vice president to the chief operating officer. Internal policy defines **reachability** in the reporting graph: an employee **can escalate to** another employee if there is a **finite chain** of direct reports (zero or more hops) from the first to the second. If an employee can escalate to the chief operating officer, then urgent capital requests from that employee are auto-approved up to the director level. Avery is a field agent. In conclusion: if Avery can escalate to the chief operating officer through the reporting chain, then Avery’s urgent capital requests are auto-approved up to the director level.

### R-2 (reject · Agent 3 target quantifier — unbounded domain)

For **every natural number** slot index k with k at least 1, warehouse rack lane A-12 has a bin at position k whose labeled capacity in kilograms is **at least** twice the index k, and if the weight on hand in that bin ever exceeds the labeled capacity then the inventory system raises a critical alert for that bin. Lane A-12 currently has no bins with negative capacity labels. Bin 47 had a critical alert yesterday. If there is **any** natural number m such that bin m carries hazmat class 4 materials, then lane A-12 is on partial lockdown until the safety audit completes. In conclusion: lane A-12 is on partial lockdown until the safety audit completes.

### R-3 (reject · Agent 3 target — vague quantifier over open class)

Most enterprise customers who upgraded to the premium analytics tier during the last two fiscal quarters also purchased the optional forecast pack, unless their procurement policy explicitly forbids add-on modules, and the finance team waived the add-on rule only for accounts flagged as strategic partnerships. **Most** self-serve retailers, however, stayed on the standard tier and never bought the forecast pack. If **most** active accounts in the EMEA region exceed their quarterly API call quota, then the platform enables throttling for all regional tenants until usage normalizes. Acme Trading is an EMEA retailer on the standard tier and has never purchased the forecast pack. In conclusion: Acme Trading is counted among the majority that stayed on the standard tier this year.

### R-4 (reject · Agent 3 target — temporal / full history)

If an aircraft has **never** completed the required pitot-static verification since its last heavy maintenance, and it has accumulated at least seventy thousand flight hours since that maintenance, and at least three independent sensor drift events were logged for the same air data computer chain during the preceding twelve months, then the aircraft is grounded until both the air data system and the pitot-static checks pass with signed maintenance releases. Bluewing 441 has seventy-one thousand flight hours since its last heavy maintenance and four drift events logged in the last year, but maintenance records show only partial pitot-static checks, not the full verification package. In conclusion: Bluewing 441 is grounded until the air data system and pitot-static checks pass with signed releases.

### R-5 (reject · Agent 3 target — higher-order / attribute quantification)

For **every criterion the procurement compliance board might adopt** when it evaluates a cloud vendor’s resilience story, if the vendor satisfies that criterion under the board’s published stress-test scenarios, then the vendor qualifies for the restricted federal data path, provided no subsidiary appears on the sanctions watchlist during the review window. Nimbus Cloud satisfies every criterion the board actually published in the April addendum, and no Nimbus subsidiary was listed during review. A subsidiary is **sanction-sensitive** if there is **some** future board meeting at which a new criterion could be introduced that the vendor would fail. If Nimbus is sanction-sensitive, the federal data path offer is void. In conclusion: Nimbus Cloud qualifies for the restricted federal data path and the offer is not void.

### R-6 (reject · Agent 2 target — dense compound operators in one rule stroke)

Every overseas supplier that ships temperature-sensitive biological reagents into at least one cold-chain port that serves at least three hospital networks **and** operates consolidation hubs in at least two countries **must** certify **every** inbound lot of **every** product family that crosses **any** of those cold-chain nodes, **and** must archive **every** temperature excursion log for **any** lot that either arrived more than six hours behind schedule **or** experienced a thaw-warning flag **or** was cleared only through an emergency deviation signed by **both** the importing site pharmacist **and** the carrier’s quality lead, **unless** the shipment was a dry-ice substitute protocol that the FDA letter explicitly exempts. Medalane Pharma is one such supplier, and lot L-903 crossed two cold-chain nodes last Tuesday with a thaw-warning flag but no dual-signed deviation. In conclusion: Medalane must archive the temperature excursion logs for lot L-903.

### E-1 (edge · Agent 2 — guard “If A and B then C” from invalid factorization)

Regional policy: **if** a borrower’s credit score is **below** six hundred **and** the borrower has **no** co-signer with a score **at least** seven hundred **and** the loan’s term exceeds **five** years, **then** the loan must be manually reviewed by an underwriter **and** cannot close automatically. River Bank approved an auto-closed mortgage for Dana, whose score is five eighty, with a six-year term and no qualifying co-signer. Every auto-closed mortgage that skips manual review violates Policy 14-B if the borrower lacks an exception code. Dana had no exception code. In conclusion: River Bank violated Policy 14-B on Dana’s loan.

### E-2 (edge · Agent 3 — open-ended symptom / “and similar complaints”)

Work-related asthma adjudication: documented symptoms include wheeze after shift change, chest tightness during cleaning with peracetic acid, exercise intolerance on stairs, morning cough, nocturnal awakenings with shortness of breath, peak-flow variability above twenty percent on home logs, and **similar respiratory complaints** not captured by the checklist. If two independent specialists document compatible findings **and** exposure history ties symptoms to the plant floor, the case is classified Tier-2 without appeal. Luis has two specialist reports and documented exposure; his file also notes **similar complaints** outside the checklist. In conclusion: Luis’s case is classified Tier-2 without appeal.

### E-3 (edge · Agent 1 / 3 — grammatically incomplete disjunction)

Either the north approach lane’s concrete batch **or** the south approach lane’s batch for Runway 09/27. Every batch poured this week either passed slump testing **or** was re-threaded with additive, and the paving superintendent signs off only when both lane certificates are on file before the overnight cure window. The north lane batch was poured this week and did not receive additive; the south lane batch was poured this week, passed slump, and has the superintendent’s sign-off. If a runway batch fails slump and gets no additive, that runway end is closed to heavy jets until a new batch is certified. In conclusion: heavy jets may still use Runway 09/27 from the south end this week.

### E-4 (edge · Agent 2/3 — biconditional + bounded arithmetic chain)

Dock scheduling at Port Vale: a berth slot is **premium** if and only if the vessel’s declared LOA is **at most** two hundred forty meters **and** its arrival window fits entirely inside the morning tide gate, **or** the harbor master issues a paid priority token for that vessel. MV **Cornelia** declared two thirty-five meters, arrived inside the morning gate, and carries a priority token. Tonnage fees are waived **if and only if** the berth is premium **and** the carrier submits manifests **at least** forty-eight hours ahead **and** no hazardous class-1 cargo is declared. **Cornelia** filed manifests fifty hours early and declared only class-3 cargo. **If** tonnage fees are waived **then** the stevedore’s lift cap increases by **twenty** percent for that call. In conclusion: **Cornelia** receives the twenty-percent lift cap increase on this call.

### E-5 (edge · Agent 2 — “Every X that is Y has Z” must stay one structured claim)

Every loan officer **that is** licensed in **both** California **and** Nevada **and** that has closed **at least** twelve rural-development deals in the **last** calendar year **has** an elevated approval ceiling of one-point-two million dollars for single-section manufactured housing, **unless** the borrower’s debt-to-income ratio **exceeds** forty-three percent **or** the census tract is flagged “infrastructure incomplete.” Jamie is licensed in both states, closed fifteen rural-development deals last year, but the subject tract is infrastructure-incomplete. The elevated ceiling **never** applies when the tract flag is set. In conclusion: Jamie may not use the elevated ceiling on this application.

### E-6 (edge · Agent 3 — nested conditional chain; should remain in-scope per prompt)

If a book is **more than** twenty-one days overdue **and** the borrower **is** a library member, **then** **if** the accrued fine **exceeds** the member’s fine cap **and** the member has **not** enrolled in the amnesty weekend, the member is **suspended** from borrowing **and** the account is flagged for desk review; **if** the member **has** enrolled in the amnesty weekend, **then** **instead** only the suspension applies until the book is returned **and** the fine is paid down to zero. Riley’s book is twenty-four days overdue, Riley is a member, the fine exceeds Riley’s cap, Riley did **not** enroll in amnesty, and the book is **not** yet returned. In conclusion: Riley’s account is flagged for desk review.
