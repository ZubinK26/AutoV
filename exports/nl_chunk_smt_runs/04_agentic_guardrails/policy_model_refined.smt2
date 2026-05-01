; ============================================================
; Bundle: nlchunksmt_20260430_214111Z_4a941dcb  |  Committed: 2026-04-30T21:41:58Z
; ============================================================
(set-logic ALL)
; ============================================================
; REFINED POLICY MODEL — do not overwrite chunk pipeline snapshots.
; Source: policy_snapshots/policy_latest.smt2
; NL: (historical) agentsim/04_agentic_guardrails.md — repo path removed; see policy_model_refined_CHANGELOG.md
; Changelog: policy_model_refined_CHANGELOG.md
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_214111Z_4a941dcb ---
(declare-sort Customer 0)
(declare-sort CustomerIdentifier 0)
(declare-sort Account 0)
(declare-sort AccountIdentifier 0)

(declare-datatype KycStatus ((verified) (pending) (failed)))
(declare-datatype AccountTier ((standard) (plus) (premium) (business)))
(declare-datatype AccountStatus ((active) (frozen) (closed) (restricted)))

(declare-fun customer-id (Customer) CustomerIdentifier)
(declare-fun kyc-status (Customer) KycStatus)
(declare-fun account-tier (Customer) AccountTier)
(declare-fun is-vulnerable (Customer) Bool)
(declare-fun is-pep (Customer) Bool)
(declare-fun has-sanctions (Customer) Bool)
(declare-fun recent-dispute-count (Customer) Int)
(declare-fun recent-goodwill-credit-total (Customer) Int)
(declare-fun has-previously-failed-doc-request (Customer) Bool)

(declare-fun account-id (Account) AccountIdentifier)
(declare-fun account-owner (Account) Customer)
(declare-fun account-status (Account) AccountStatus)

; Rule: r_9738387f5074  |  Line: 0
; NL: "Every customer is identified by exactly one unique customer identifier."
(assert (forall ((c1 Customer) (c2 Customer))
  (=> (= (customer-id c1) (customer-id c2)) (= c1 c2))))

; Rule: r_15469c7c7c49  |  Line: 1
; NL: "Every customer has exactly one KYC status that is one of: VERIFIED, PENDING, or FAILED."
(assert (forall ((c Customer))
  (or (= (kyc-status c) verified)
      (= (kyc-status c) pending)
      (= (kyc-status c) failed))))

; Rule: r_ff0af67718d0  |  Line: 2
; NL: "Every customer has exactly one account tier that is one of: STANDARD, PLUS, PREMIUM, or BUSINESS."
(assert (forall ((c Customer))
  (or (= (account-tier c) standard)
      (= (account-tier c) plus)
      (= (account-tier c) premium)
      (= (account-tier c) business))))

; Rule: r_ce16208e5587  |  Line: 3
; NL: "Every customer has exactly one vulnerable flag that is either true or false."
(assert (forall ((c Customer))
  (or (= (is-vulnerable c) true)
      (= (is-vulnerable c) false))))

; Rule: r_63565e99e8c2  |  Line: 4
; NL: "Every customer has exactly one politically exposed person flag that is either true or false."
(assert (forall ((c Customer))
  (or (= (is-pep c) true)
      (= (is-pep c) false))))

; Rule: r_dfcb31041944  |  Line: 5
; NL: "Every customer has exactly one sanctions flag that is either true or false."
(assert (forall ((c Customer))
  (or (= (has-sanctions c) true)
      (= (has-sanctions c) false))))

; Rule: r_03f95663924b  |  Line: 6
; NL: "Every customer has exactly one recent dispute count field, which is a non-negative integer maintained by the runtime."
(assert (forall ((c Customer))
  (>= (recent-dispute-count c) 0)))

; Rule: r_01c5982f926d  |  Line: 7
; NL: "Every customer has exactly one recent goodwill credit total field, which is a non-negative amount in pence maintained by the runtime."
(assert (forall ((c Customer))
  (>= (recent-goodwill-credit-total c) 0)))

; Rule: r_800aa5cb460c  |  Line: 8
; NL: "Every customer has exactly one has previously failed documentation request field, which is a boolean maintained by the runtime."
(assert (forall ((c Customer))
  (or (= (has-previously-failed-doc-request c) true)
      (= (has-previously-failed-doc-request c) false))))

; Rule: r_0e83394632a8  |  Line: 9
; NL: "Every account is identified by exactly one unique account identifier."
(assert (forall ((a1 Account) (a2 Account))
  (=> (= (account-id a1) (account-id a2)) (= a1 a2))))

; Rule: r_bd951d3cfe89  |  Line: 10
; NL: "Every account belongs to exactly one customer."
(assert (forall ((a Account))
  (exists ((c Customer)) (= (account-owner a) c))))

; Rule: r_780997e2a0fc  |  Line: 11
; NL: "Every account has exactly one status that is one of: ACTIVE, FROZEN, CLOSED, or RESTRICTED."
(assert (forall ((a Account))
  (or (= (account-status a) active)
      (= (account-status a) frozen)
      (= (account-status a) closed)
      (= (account-status a) restricted))))

; ============================================================
; Bundle: nlchunksmt_20260430_214208Z_c5f5ede0  |  Committed: 2026-04-30T21:43:27Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_214208Z_c5f5ede0 ---
(declare-fun active-restriction-count (Account) Int)

(declare-sort Card 0)
(declare-sort CardIdentifier 0)
(declare-fun card-id (Card) CardIdentifier)
(declare-fun card-account (Card) Account)

(declare-datatype CardStatus ((card-active) (card-frozen) (card-blocked) (card-cancelled) (card-expired)))
(declare-fun card-status (Card) CardStatus)

(declare-sort Transaction 0)
(declare-sort TransactionIdentifier 0)
(declare-fun transaction-id (Transaction) TransactionIdentifier)
(declare-fun transaction-account (Transaction) Account)
(declare-fun transaction-amount-pence (Transaction) Int)
(declare-fun is-debit (Transaction) Bool)
(declare-fun is-credit (Transaction) Bool)

(declare-datatype TransactionStatus ((txn-pending) (txn-posted) (txn-reversed) (txn-disputed)))
(declare-fun transaction-status (Transaction) TransactionStatus)

(declare-fun days-since-posted (Transaction) Int)
(declare-fun has-duplicate-candidate-within-window (Transaction) Bool)
(declare-fun is-section-75-eligible (Transaction) Bool)
(declare-fun chargeback-window-days (Transaction) Int)

; Rule: r_5482a365460c  |  Line: 0
; NL: "Every account has zero or more active restrictions."
(assert (forall ((a Account))
  (>= (active-restriction-count a) 0)))

; Rule: r_e06a6857e733  |  Line: 1
; NL: "Every card is identified by a unique card identifier."
(assert (forall ((c1 Card) (c2 Card))
  (=> (= (card-id c1) (card-id c2)) (= c1 c2))))

; Rule: r_043a3df228e0  |  Line: 2
; NL: "Every card belongs to exactly one account."
(assert (forall ((c Card))
  (exists ((a Account)) (= (card-account c) a))))

; Rule: r_a60f4990b114  |  Line: 3
; NL: "Every card has exactly one status that is one of: ACTIVE, FROZEN, BLOCKED, CANCELLED, or EXPIRED."
(assert (forall ((c Card))
  (or (= (card-status c) card-active)
      (= (card-status c) card-frozen)
      (= (card-status c) card-blocked)
      (= (card-status c) card-cancelled)
      (= (card-status c) card-expired))))

; Rule: r_7408a814b54d  |  Line: 4
; NL: "Every transaction is identified by a unique transaction identifier."
(assert (forall ((t1 Transaction) (t2 Transaction))
  (=> (= (transaction-id t1) (transaction-id t2)) (= t1 t2))))

; Rule: r_0d1d57ff1481  |  Line: 5
; NL: "Every transaction belongs to exactly one account."
(assert (forall ((t Transaction))
  (exists ((a Account)) (= (transaction-account t) a))))

; Rule: r_e8f2c899205b  |  Line: 6  [REFINED — see CHANGELOG R3, R12, R15]
; NL: "Every transaction has exactly one amount in pence." (single Int + debit/credit discipline)
; REFINED: exclude debit and credit both true; POSTED / DISPUTED / REVERSED require exactly one classification (NL line 16).
(assert (forall ((t Transaction))
  (not (and (is-debit t) (is-credit t)))))
(assert (forall ((t Transaction))
  (=> (or (= (transaction-status t) txn-posted)
          (= (transaction-status t) txn-disputed)
          (= (transaction-status t) txn-reversed))
      (xor (is-debit t) (is-credit t)))))

; Rule: r_259c01b7b471  |  Line: 7
; NL: "The amount in pence of every debit transaction is a positive integer."
(assert (forall ((t Transaction))
  (=> (is-debit t) (> (transaction-amount-pence t) 0))))

; Rule: r_fff3b87d55eb  |  Line: 8
; NL: "The amount in pence of every credit transaction is a negative integer."
(assert (forall ((t Transaction))
  (=> (is-credit t) (< (transaction-amount-pence t) 0))))

; Rule: r_c32c39dbd0ad  |  Line: 9
; NL: "Every transaction has exactly one status that is one of: PENDING, POSTED, REVERSED, or DISPUTED."
(assert (forall ((t Transaction))
  (or (= (transaction-status t) txn-pending)
      (= (transaction-status t) txn-posted)
      (= (transaction-status t) txn-reversed)
      (= (transaction-status t) txn-disputed))))

; Rule: r_6b6f82808a95  |  Line: 10  [REFINED — CHANGELOG R4]
; NL: "Every transaction has exactly one field named days since posted."
; REFINED: id-extensionality (non-vacuous).
(assert (forall ((t1 Transaction) (t2 Transaction))
  (=> (= (transaction-id t1) (transaction-id t2))
      (= (days-since-posted t1) (days-since-posted t2)))))

; Rule: r_9209435c4276  |  Line: 11  [+ REFINE R13, R16 — see CHANGELOG]
; NL: "The field named days since posted of every transaction is a non-negative integer maintained by the runtime."
(assert (forall ((t Transaction))
  (>= (days-since-posted t) 0)))
; REFINE R13: PENDING — no posted date yet; keeps queries/maps from inventing a positive "days since" pre-posting.
(assert (forall ((t Transaction))
  (=> (= (transaction-status t) txn-pending)
      (= (days-since-posted t) 0))))
; REFINE R16: REVERSED — posting-age field cleared for policy windows keyed off “days since posted” (see CHANGELOG).
(assert (forall ((t Transaction))
  (=> (= (transaction-status t) txn-reversed)
      (= (days-since-posted t) 0))))

; Rule: r_1aa2ea99aa9d  |  Line: 12
; NL: "Every transaction has exactly one field named has duplicate candidate within window."
(assert (forall ((t Transaction))
  (or (= (has-duplicate-candidate-within-window t) true)
      (= (has-duplicate-candidate-within-window t) false))))

; Rule: r_821b9946980e  |  Line: 13  [REFINED — CHANGELOG R7]
; NL: "The field named has duplicate candidate within window of every transaction is a boolean maintained by the runtime."
; REFINED: duplicate assert removed (totality already in r_1aa2ea99aa9d).

; Rule: r_44bed1337363  |  Line: 14
; NL: "Every transaction has exactly one section seventy five eligibility flag that is either true or false."
(assert (forall ((t Transaction))
  (or (= (is-section-75-eligible t) true)
      (= (is-section-75-eligible t) false))))

; Rule: r_ff0b24be07d3  |  Line: 15  [REFINED — CHANGELOG R5]
; NL: "Every transaction has exactly one chargeback window in days."
; REFINED: id-extensionality replaces tautology.
(assert (forall ((t1 Transaction) (t2 Transaction))
  (=> (= (transaction-id t1) (transaction-id t2))
      (= (chargeback-window-days t1) (chargeback-window-days t2)))))

; Rule: r_602b7e397edf  |  Line: 16
; NL: "The chargeback window in days of every transaction is a non-negative integer."
(assert (forall ((t Transaction))
  (>= (chargeback-window-days t) 0)))

; ============================================================
; Bundle: nlchunksmt_20260430_221033Z_0214135a  |  Committed: 2026-04-30T22:11:45Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_221033Z_0214135a ---
(declare-fun fee-already-reversed (Transaction) Bool)

(declare-sort Dispute 0)
(declare-sort DisputeIdentifier 0)
(declare-fun dispute-id (Dispute) DisputeIdentifier)
(declare-fun dispute-transaction (Dispute) Transaction)

(declare-datatype DisputeType ((unauthorized) (merchant-refused) (goods-not-received) (goods-not-as-described) (section-75) (duplicate-charge)))
(declare-fun dispute-type (Dispute) DisputeType)

(declare-datatype DisputeStatus ((dispute-open) (dispute-under-review) (dispute-approved) (dispute-rejected) (dispute-escalated) (dispute-withdrawn)))
(declare-fun dispute-status (Dispute) DisputeStatus)

(declare-sort Refund 0)
(declare-sort RefundIdentifier 0)
(declare-fun refund-id (Refund) RefundIdentifier)
(declare-fun refund-amount-pence (Refund) Int)

(declare-datatype RefundType ((merchant-refund) (dispute-refund) (section-75-refund) (goodwill-credit) (fee-reversal)))
(declare-fun refund-type (Refund) RefundType)

(declare-sort Restriction 0)
(declare-sort RestrictionIdentifier 0)
(declare-fun restriction-id (Restriction) RestrictionIdentifier)

(declare-datatype RestrictionType ((aml-review) (fraud-hold) (sanctions-block) (court-order) (compliance-review) (customer-requested)))
(declare-fun restriction-type (Restriction) RestrictionType)
(declare-fun human-action-required (Restriction) Bool)

(declare-sort FraudReport 0)
(declare-sort FraudReportIdentifier 0)
(declare-fun fraud-report-id (FraudReport) FraudReportIdentifier)

(declare-datatype FraudReportStatus ((fraud-reported) (fraud-investigating) (fraud-confirmed) (fraud-rejected)))
(declare-fun fraud-report-status (FraudReport) FraudReportStatus)

(declare-sort ConsumerDutyAssessment 0)
(declare-sort AssessmentIdentifier 0)
(declare-fun assessment-id (ConsumerDutyAssessment) AssessmentIdentifier)
(declare-fun fair-value-check-passed (ConsumerDutyAssessment) Bool)
(declare-fun clear-communication-check-passed (ConsumerDutyAssessment) Bool)

; Rule: r_59afbfc8df06  |  Line: 0
; NL: "Every transaction has exactly one field named fee already reversed."
(assert (forall ((t Transaction))
  (or (= (fee-already-reversed t) true)
      (= (fee-already-reversed t) false))))

; Rule: r_47f5c56afea2  |  Line: 1  [REFINED — CHANGELOG R8]
; NL: "The field named fee already reversed of a transaction is a boolean maintained by the runtime."
; REFINED: duplicate totality removed (see r_59afbfc8df06).

; Rule: r_a4b864c681aa  |  Line: 2
; NL: "Every dispute is identified by a unique dispute identifier."
(assert (forall ((d1 Dispute) (d2 Dispute))
  (=> (= (dispute-id d1) (dispute-id d2)) (= d1 d2))))

; Rule: r_118b1f2ef439  |  Line: 3
; NL: "Every dispute references exactly one transaction."
(assert (forall ((d Dispute))
  (exists ((t Transaction)) (= (dispute-transaction d) t))))

; Rule: r_eb17fdba6620  |  Line: 4
; NL: "Every dispute has exactly one type that is one of: UNAUTHORIZED, MERCHANT_REFUSED, GOODS_NOT_RECEIVED, GOODS_NOT_AS_DESCRIBED, SECTION_75, or DUPLICATE_CHARGE."
(assert (forall ((d Dispute))
  (or (= (dispute-type d) unauthorized)
      (= (dispute-type d) merchant-refused)
      (= (dispute-type d) goods-not-received)
      (= (dispute-type d) goods-not-as-described)
      (= (dispute-type d) section-75)
      (= (dispute-type d) duplicate-charge))))

; Rule: r_b22d606fed6c  |  Line: 5
; NL: "Every dispute has exactly one status that is one of: OPEN, UNDER_REVIEW, APPROVED, REJECTED, ESCALATED, or WITHDRAWN."
(assert (forall ((d Dispute))
  (or (= (dispute-status d) dispute-open)
      (= (dispute-status d) dispute-under-review)
      (= (dispute-status d) dispute-approved)
      (= (dispute-status d) dispute-rejected)
      (= (dispute-status d) dispute-escalated)
      (= (dispute-status d) dispute-withdrawn))))

; Rule: r_90e497cfa88e  |  Line: 6
; NL: "Every refund is identified by a unique refund identifier."
(assert (forall ((r1 Refund) (r2 Refund))
  (=> (= (refund-id r1) (refund-id r2)) (= r1 r2))))

; Rule: r_25453c863569  |  Line: 7  [REFINED — CHANGELOG R6]
; NL: "Every refund has exactly one amount in pence."
; REFINED: refund-id extensionality replaces tautology.
(assert (forall ((r1 Refund) (r2 Refund))
  (=> (= (refund-id r1) (refund-id r2))
      (= (refund-amount-pence r1) (refund-amount-pence r2)))))

; Rule: r_49b3fa265a71  |  Line: 8
; NL: "The amount in pence of a refund is a positive integer."
(assert (forall ((r Refund))
  (> (refund-amount-pence r) 0)))

; Rule: r_0173c6f4e8ac  |  Line: 9
; NL: "Every refund has exactly one type that is one of: MERCHANT_REFUND, DISPUTE_REFUND, SECTION_75_REFUND, GOODWILL_CREDIT, or FEE_REVERSAL."
(assert (forall ((r Refund))
  (or (= (refund-type r) merchant-refund)
      (= (refund-type r) dispute-refund)
      (= (refund-type r) section-75-refund)
      (= (refund-type r) goodwill-credit)
      (= (refund-type r) fee-reversal))))

; Rule: r_ddafadd74eec  |  Line: 10
; NL: "Every restriction is identified by a unique restriction identifier."
(assert (forall ((r1 Restriction) (r2 Restriction))
  (=> (= (restriction-id r1) (restriction-id r2)) (= r1 r2))))

; Rule: r_d3e1db507b04  |  Line: 11
; NL: "Every restriction has exactly one type that is one of: AML_REVIEW, FRAUD_HOLD, SANCTIONS_BLOCK, COURT_ORDER, COMPLIANCE_REVIEW, or CUSTOMER_REQUESTED."
(assert (forall ((r Restriction))
  (or (= (restriction-type r) aml-review)
      (= (restriction-type r) fraud-hold)
      (= (restriction-type r) sanctions-block)
      (= (restriction-type r) court-order)
      (= (restriction-type r) compliance-review)
      (= (restriction-type r) customer-requested))))

; Rule: r_8445c68240e9  |  Line: 12
; NL: "Every restriction has exactly one flag indicating whether human action is required to lift the restriction."
(assert (forall ((r Restriction))
  (or (= (human-action-required r) true)
      (= (human-action-required r) false))))

; Rule: r_1e637176ab71  |  Line: 13
; NL: "Every fraud report is identified by a unique fraud report identifier."
(assert (forall ((f1 FraudReport) (f2 FraudReport))
  (=> (= (fraud-report-id f1) (fraud-report-id f2)) (= f1 f2))))

; Rule: r_542c97b11a8b  |  Line: 14
; NL: "Every fraud report has exactly one status that is one of: REPORTED, INVESTIGATING, CONFIRMED, or REJECTED."
(assert (forall ((f FraudReport))
  (or (= (fraud-report-status f) fraud-reported)
      (= (fraud-report-status f) fraud-investigating)
      (= (fraud-report-status f) fraud-confirmed)
      (= (fraud-report-status f) fraud-rejected))))

; Rule: r_8107a28b08d2  |  Line: 15
; NL: "Every consumer duty assessment is identified by a unique assessment identifier."
(assert (forall ((a1 ConsumerDutyAssessment) (a2 ConsumerDutyAssessment))
  (=> (= (assessment-id a1) (assessment-id a2)) (= a1 a2))))

; Rule: r_c17f65086713  |  Line: 16
; NL: "Every consumer duty assessment records whether a fair value check passed."
(assert (forall ((a ConsumerDutyAssessment))
  (or (= (fair-value-check-passed a) true)
      (= (fair-value-check-passed a) false))))

; Rule: r_a629e29703e0  |  Line: 17
; NL: "Every consumer duty assessment records whether a clear communication check passed."
(assert (forall ((a ConsumerDutyAssessment))
  (or (= (clear-communication-check-passed a) true)
      (= (clear-communication-check-passed a) false))))

; ============================================================
; Bundle: nlchunksmt_20260430_221222Z_945285c5  |  Committed: 2026-04-30T22:16:53Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_221222Z_945285c5 ---
(declare-sort Interaction 0)
(declare-const current-interaction Interaction)
(declare-fun has-been-escalated (Interaction) Bool)

(declare-sort ToolCall 0)
(declare-fun is-write-tool-call (ToolCall) Bool)
(declare-fun has-typed-parameters (ToolCall) Bool)

(declare-fun is-apply-refund-call (ToolCall) Bool)
(declare-fun refund-call-customer (ToolCall) Customer)
(declare-fun refund-call-account (ToolCall) Account)
(declare-fun refund-call-type (ToolCall) RefundType)
(declare-fun refund-call-transaction (ToolCall) Transaction)
(declare-fun refund-call-amount-pence (ToolCall) Int)

(declare-fun customer-exists-in-db (Customer) Bool)
(declare-fun account-exists-in-db (Account) Bool)
(declare-fun transaction-exists-in-db (Transaction) Bool)

(declare-fun requires-human-approval (ToolCall) Bool)
(declare-fun is-permitted (ToolCall) Bool)


; --- REFINEMENT: human approval gates is-permitted (see CHANGELOG R2) ---
(declare-fun human-approval-granted (ToolCall) Bool)
(assert (forall ((tc ToolCall))
  (=> (and (requires-human-approval tc) (not (human-approval-granted tc)))
      (not (is-permitted tc)))))
; Rule: r_e5dd966343f5  |  Line: 0
; NL: "The current interaction has a field named 'has been escalated' which is a boolean value maintained by the runtime."
(assert (or (= (has-been-escalated current-interaction) true)
            (= (has-been-escalated current-interaction) false)))

; Rule: r_ba83a7075278  |  Line: 1
; NL: "Every tool call is one of the defined write tool calls."
(assert (forall ((tc ToolCall))
  (is-write-tool-call tc)))

; Rule: r_d03d9ed02079  |  Line: 2
; NL: "Every tool call carries typed parameters."
(assert (forall ((tc ToolCall))
  (has-typed-parameters tc)))

; Rule: r_1712cb89175f  |  Line: 3
; NL: "Every call to apply a refund of any type requires that the affected customer exists in the database."
(assert (forall ((tc ToolCall))
  (=> (is-apply-refund-call tc)
      (customer-exists-in-db (refund-call-customer tc)))))

; Rule: r_485a76fe439b  |  Line: 4
; NL: "Every call to apply a refund of any type requires that the affected account exists in the database."
(assert (forall ((tc ToolCall))
  (=> (is-apply-refund-call tc)
      (account-exists-in-db (refund-call-account tc)))))

; Rule: r_5c43b9a01df8  |  Line: 5
; NL: "Every call to apply a refund where the refund type is MERCHANT_REFUND requires that the referenced transaction exists in the database."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc) (= (refund-call-type tc) merchant-refund))
      (transaction-exists-in-db (refund-call-transaction tc)))))

; Rule: r_b40a67da1d57  |  Line: 6
; NL: "Every call to apply a refund where the refund type is DISPUTE_REFUND requires that the referenced transaction exists in the database."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc) (= (refund-call-type tc) dispute-refund))
      (transaction-exists-in-db (refund-call-transaction tc)))))

; Rule: r_819bc84ad524  |  Line: 7
; NL: "Every call to apply a refund where the refund type is SECTION_75_REFUND requires that the referenced transaction exists in the database."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc) (= (refund-call-type tc) section-75-refund))
      (transaction-exists-in-db (refund-call-transaction tc)))))

; Rule: r_45c9ba721a09  |  Line: 8
; NL: "Every call to apply a refund where the refund type is MERCHANT_REFUND requires that the referenced transaction has a status of either POSTED or DISPUTED."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc) (= (refund-call-type tc) merchant-refund))
      (or (= (transaction-status (refund-call-transaction tc)) txn-posted)
          (= (transaction-status (refund-call-transaction tc)) txn-disputed)))))

; Rule: r_8d5ca5ecf71b  |  Line: 9
; NL: "Every call to apply a refund where the refund type is DISPUTE_REFUND requires that the referenced transaction has a status of either POSTED or DISPUTED."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc) (= (refund-call-type tc) dispute-refund))
      (or (= (transaction-status (refund-call-transaction tc)) txn-posted)
          (= (transaction-status (refund-call-transaction tc)) txn-disputed)))))

; Rule: r_d65db1f953eb  |  Line: 10
; NL: "Every call to apply a refund where the refund type is SECTION_75_REFUND requires that the referenced transaction has a status of either POSTED or DISPUTED."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc) (= (refund-call-type tc) section-75-refund))
      (or (= (transaction-status (refund-call-transaction tc)) txn-posted)
          (= (transaction-status (refund-call-transaction tc)) txn-disputed)))))

; Rule: r_78f23ea79ded  |  Line: 11
; NL: "Every call to apply a refund where the refund type is SECTION_75_REFUND requires that the referenced transaction has its section seventy-five eligibility flag set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc) (= (refund-call-type tc) section-75-refund))
      (= (is-section-75-eligible (refund-call-transaction tc)) true))))

; Rule: r_626e45bcd412  |  Line: 12
; NL: "Every call to apply a refund where the refund type is DISPUTE_REFUND requires that an open dispute referencing the same transaction exists with a status of APPROVED."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc) (= (refund-call-type tc) dispute-refund))
      (exists ((d Dispute))
        (and (= (dispute-transaction d) (refund-call-transaction tc))
             (= (dispute-status d) dispute-approved))))))

; Rule: r_fa6a4ee31c45  |  Line: 13
; NL: "Every call to apply a refund of any type with an amount greater than fifty thousand pence requires human approval."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc) (> (refund-call-amount-pence tc) 50000))
      (requires-human-approval tc))))

; Rule: r_d4479aac5056  |  Line: 14  [REFINED — CHANGELOG R9, R14]
; NL: "Every call to apply a refund of any type with an amount greater than the original transaction amount is not permitted."
; REFINED: only enforce when referenced transaction exists in DB (original posting is real); magnitude from signed amount (NL 16, 42).
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (transaction-exists-in-db (refund-call-transaction tc))
           (> (refund-call-amount-pence tc)
              (ite (>= (transaction-amount-pence (refund-call-transaction tc)) 0)
                   (transaction-amount-pence (refund-call-transaction tc))
                   (- 0 (transaction-amount-pence (refund-call-transaction tc))))))
      (not (is-permitted tc)))))

; ============================================================
; Bundle: nlchunksmt_20260430_222310Z_6dfadb65  |  Committed: 2026-04-30T22:24:20Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_222310Z_6dfadb65 ---
(declare-fun restriction-account (Restriction) Account)
(declare-fun is-active-restriction (Restriction) Bool)

; REFINE R18 (CHANGELOG): non-negative count reflects presence of at least one active restriction on that account.
(assert (forall ((a Account))
  (let ((c (active-restriction-count a)))
    (= (>= c 1)
       (exists ((r Restriction))
         (and (= (restriction-account r) a)
              (= (is-active-restriction r) true)))))))

(declare-fun assessment-interaction (ConsumerDutyAssessment) Interaction)
(declare-fun is-fee (Transaction) Bool)
(declare-fun is-initiate-dispute-call (ToolCall) Bool)
(declare-fun dispute-call-transaction (ToolCall) Transaction)

; Rule: r_dc9503bda251  |  Line: 0
; NL: "Every call to apply a goodwill credit with an amount greater than ten thousand pence requires human approval."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (refund-call-type tc) goodwill-credit)
           (> (refund-call-amount-pence tc) 10000))
      (requires-human-approval tc))))

; Rule: r_a9a969f4e92f  |  Line: 1
; NL: "Every call to apply a goodwill credit is not permitted if the affected customer's recent goodwill credit total exceeds fifty thousand pence."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (refund-call-type tc) goodwill-credit)
           (> (recent-goodwill-credit-total (refund-call-customer tc)) 50000))
      (not (is-permitted tc)))))

; Rule: r_7c99ebf69e12  |  Line: 2
; NL: "Every call to apply a refund is not permitted if the affected account has at least one active restriction of type SANCTIONS_BLOCK."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (exists ((r Restriction))
             (and (= (restriction-account r) (refund-call-account tc))
                  (= (is-active-restriction r) true)
                  (= (restriction-type r) sanctions-block))))
      (not (is-permitted tc)))))

; Rule: r_8aff285fec17  |  Line: 3
; NL: "Every call to apply a goodwill credit is not permitted if the affected account has at least one active restriction of type SANCTIONS_BLOCK."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (refund-call-type tc) goodwill-credit)
           (exists ((r Restriction))
             (and (= (restriction-account r) (refund-call-account tc))
                  (= (is-active-restriction r) true)
                  (= (restriction-type r) sanctions-block))))
      (not (is-permitted tc)))))

; Rule: r_abe379033813  |  Line: 4
; NL: "Every call to apply a refund is not permitted if the affected account has at least one active restriction of type COURT_ORDER."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (exists ((r Restriction))
             (and (= (restriction-account r) (refund-call-account tc))
                  (= (is-active-restriction r) true)
                  (= (restriction-type r) court-order))))
      (not (is-permitted tc)))))

; Rule: r_ac11433ec54a  |  Line: 5
; NL: "Every call to apply a goodwill credit is not permitted if the affected account has at least one active restriction of type COURT_ORDER."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (refund-call-type tc) goodwill-credit)
           (exists ((r Restriction))
             (and (= (restriction-account r) (refund-call-account tc))
                  (= (is-active-restriction r) true)
                  (= (restriction-type r) court-order))))
      (not (is-permitted tc)))))

; Rule: r_1fe6b3c958f9  |  Line: 6
; NL: "Every call to apply a refund of any type where the affected customer has a vulnerable flag set to true requires that at least one consumer duty assessment exists for the current interaction."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (is-vulnerable (refund-call-customer tc)) true))
      (exists ((a ConsumerDutyAssessment))
        (= (assessment-interaction a) current-interaction)))))

; Rule: r_88019749c8a3  |  Line: 7
; NL: "Every call to apply a fee reversal requires that the referenced transaction has a positive amount."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (refund-call-type tc) fee-reversal))
      (> (transaction-amount-pence (refund-call-transaction tc)) 0))))

; Rule: r_ec3ad479e75b  |  Line: 8
; NL: "Every call to apply a fee reversal requires that the referenced transaction is classified as a fee."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (refund-call-type tc) fee-reversal))
      (= (is-fee (refund-call-transaction tc)) true))))

; Rule: r_247e64c18016  |  Line: 9
; NL: "Every call to apply a fee reversal is not permitted if the referenced transaction's fee already reversed flag is set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (refund-call-type tc) fee-reversal)
           (= (fee-already-reversed (refund-call-transaction tc)) true))
      (not (is-permitted tc)))))

; Rule: r_317c5792c6ba  |  Line: 10
; NL: "Every call to initiate a dispute requires that the referenced transaction exists."
(assert (forall ((tc ToolCall))
  (=> (is-initiate-dispute-call tc)
      (= (transaction-exists-in-db (dispute-call-transaction tc)) true))))

; Rule: r_c43d80786e8b  |  Line: 11
; NL: "Every call to initiate a dispute requires that the referenced transaction has a status of POSTED."
(assert (forall ((tc ToolCall))
  (=> (is-initiate-dispute-call tc)
      (= (transaction-status (dispute-call-transaction tc)) txn-posted))))

; Rule: r_6f4f6048a1e2  |  Line: 12  [REFINED — CHANGELOG R17]
; NL: "Every call to initiate a dispute requires that no other open dispute exists for the referenced transaction."
; REFINED: also block parallel UNDER_REVIEW (operational alignment; NL line 53 may be tightened to match).
(assert (forall ((tc ToolCall))
  (=> (is-initiate-dispute-call tc)
      (not (exists ((d Dispute))
             (and (= (dispute-transaction d) (dispute-call-transaction tc))
                  (or (= (dispute-status d) dispute-open)
                      (= (dispute-status d) dispute-under-review))))))))

; ============================================================
; Bundle: nlchunksmt_20260430_222444Z_12b9dfc7  |  Committed: 2026-04-30T22:25:55Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_222444Z_12b9dfc7 ---
(declare-fun dispute-call-type (ToolCall) DisputeType)
(declare-fun dispute-call-customer (ToolCall) Customer)

(declare-fun is-cancel-dispute-call (ToolCall) Bool)
(declare-fun cancel-dispute-call-dispute (ToolCall) Dispute)
(declare-fun dispute-exists-in-db (Dispute) Bool)

(declare-fun is-freeze-card-call (ToolCall) Bool)
(declare-fun freeze-card-call-card (ToolCall) Card)
(declare-fun card-exists-in-db (Card) Bool)

; Rule: r_9efd4a4bf3fd  |  Line: 0
; NL: "Every call to initiate a dispute of type SECTION_75 requires that the referenced transaction has its section seventy five eligibility flag set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-initiate-dispute-call tc) (= (dispute-call-type tc) section-75))
      (= (is-section-75-eligible (dispute-call-transaction tc)) true))))

; Rule: r_35c9c9c33202 + r_5331803ca11a  |  Lines 1–2  [REFINED — CHANGELOG R10]
; NL: "Every call to initiate a dispute of type SECTION_75 requires that the referenced transaction amount is at least ten thousand pence and at most thirty million pence."
; REFINED: bounds apply to absolute pence magnitude (credits stored negative per NL line 16).
(assert (forall ((tc ToolCall))
  (=> (and (is-initiate-dispute-call tc) (= (dispute-call-type tc) section-75))
      (and
       (>= (ite (>= (transaction-amount-pence (dispute-call-transaction tc)) 0)
                (transaction-amount-pence (dispute-call-transaction tc))
                (- 0 (transaction-amount-pence (dispute-call-transaction tc)))) 10000)
       (<= (ite (>= (transaction-amount-pence (dispute-call-transaction tc)) 0)
                (transaction-amount-pence (dispute-call-transaction tc))
                (- 0 (transaction-amount-pence (dispute-call-transaction tc)))) 30000000)))))

; Rule: r_3d548f66024b  |  Line: 3
; NL: "Every call to initiate a dispute of type UNAUTHORIZED requires that the referenced transaction's days since posted is at most one hundred twenty."
(assert (forall ((tc ToolCall))
  (=> (and (is-initiate-dispute-call tc) (= (dispute-call-type tc) unauthorized))
      (<= (days-since-posted (dispute-call-transaction tc)) 120))))

; Rule: r_9d0ce5c39737  |  Line: 4
; NL: "Every call to initiate a dispute of type GOODS_NOT_RECEIVED requires that the referenced transaction's days since posted is at least fifteen."
(assert (forall ((tc ToolCall))
  (=> (and (is-initiate-dispute-call tc) (= (dispute-call-type tc) goods-not-received))
      (>= (days-since-posted (dispute-call-transaction tc)) 15))))

; Rule: r_a40aca390415  |  Line: 5
; NL: "Every call to initiate a dispute of type DUPLICATE_CHARGE requires that the referenced transaction's has duplicate candidate within window flag is set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-initiate-dispute-call tc) (= (dispute-call-type tc) duplicate-charge))
      (= (has-duplicate-candidate-within-window (dispute-call-transaction tc)) true))))

; Rule: r_b6db1741013a  |  Line: 6
; NL: "Every call to initiate a dispute is not permitted if the customer's recent dispute count exceeds ten, unless the dispute type is UNAUTHORIZED."
(assert (forall ((tc ToolCall))
  (=> (and (is-initiate-dispute-call tc)
           (> (recent-dispute-count (dispute-call-customer tc)) 10)
           (not (= (dispute-call-type tc) unauthorized)))
      (not (is-permitted tc)))))

; Rule: r_c5fd6692925e  |  Line: 7
; NL: "Every call to initiate a dispute is not permitted if the customer's KYC status is FAILED."
(assert (forall ((tc ToolCall))
  (=> (and (is-initiate-dispute-call tc)
           (= (kyc-status (dispute-call-customer tc)) failed))
      (not (is-permitted tc)))))

; Rule: r_060520fce93a  |  Line: 8
; NL: "Every call to cancel a dispute requires that the dispute exists."
(assert (forall ((tc ToolCall))
  (=> (is-cancel-dispute-call tc)
      (= (dispute-exists-in-db (cancel-dispute-call-dispute tc)) true))))

; Rule: r_61940010595a  |  Line: 9
; NL: "Every call to cancel a dispute requires that the dispute has a status of either OPEN or UNDER_REVIEW."
(assert (forall ((tc ToolCall))
  (=> (is-cancel-dispute-call tc)
      (or (= (dispute-status (cancel-dispute-call-dispute tc)) dispute-open)
          (= (dispute-status (cancel-dispute-call-dispute tc)) dispute-under-review)))))

; Rule: r_23665cdf44f0  |  Line: 10
; NL: "Every call to cancel a dispute is not permitted if the dispute has a status of APPROVED."
(assert (forall ((tc ToolCall))
  (=> (and (is-cancel-dispute-call tc)
           (= (dispute-status (cancel-dispute-call-dispute tc)) dispute-approved))
      (not (is-permitted tc)))))

; Rule: r_423b66af09f6  |  Line: 11
; NL: "Every call to cancel a dispute is not permitted if the dispute has a status of REJECTED."
(assert (forall ((tc ToolCall))
  (=> (and (is-cancel-dispute-call tc)
           (= (dispute-status (cancel-dispute-call-dispute tc)) dispute-rejected))
      (not (is-permitted tc)))))

; Rule: r_f62dc66440c3  |  Line: 12
; NL: "Every call to cancel a dispute is not permitted if the dispute has a status of ESCALATED."
(assert (forall ((tc ToolCall))
  (=> (and (is-cancel-dispute-call tc)
           (= (dispute-status (cancel-dispute-call-dispute tc)) dispute-escalated))
      (not (is-permitted tc)))))

; Rule: r_ccad4bd72ea5  |  Line: 13
; NL: "Every call to cancel a dispute is not permitted if the dispute has a status of WITHDRAWN."
(assert (forall ((tc ToolCall))
  (=> (and (is-cancel-dispute-call tc)
           (= (dispute-status (cancel-dispute-call-dispute tc)) dispute-withdrawn))
      (not (is-permitted tc)))))

; Rule: r_6ad842e370e6  |  Line: 14
; NL: "Every call to freeze a card requires that the card exists."
(assert (forall ((tc ToolCall))
  (=> (is-freeze-card-call tc)
      (= (card-exists-in-db (freeze-card-call-card tc)) true))))

; ============================================================
; Bundle: nlchunksmt_20260430_222620Z_f2d6e4c3  |  Committed: 2026-04-30T22:27:14Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_222620Z_f2d6e4c3 ---
(declare-fun is-unfreeze-card-call (ToolCall) Bool)
(declare-fun unfreeze-card-call-card (ToolCall) Card)
(declare-fun is-apply-restriction-call (ToolCall) Bool)
(declare-fun apply-restriction-call-account (ToolCall) Account)
(declare-fun apply-restriction-call-type (ToolCall) RestrictionType)

; Rule: r_267f4a2177f2  |  Line: 0
; NL: "Every call to freeze a card requires that the target card has the status ACTIVE."
(assert (forall ((tc ToolCall))
  (=> (is-freeze-card-call tc)
      (= (card-status (freeze-card-call-card tc)) card-active))))

; Rule: r_2bce91843ab9  |  Line: 1
; NL: "Every call to unfreeze a card requires that the target card exists."
(assert (forall ((tc ToolCall))
  (=> (is-unfreeze-card-call tc)
      (= (card-exists-in-db (unfreeze-card-call-card tc)) true))))

; Rule: r_b9fa1d18a240  |  Line: 2
; NL: "Every call to unfreeze a card requires that the target card has the status FROZEN."
(assert (forall ((tc ToolCall))
  (=> (is-unfreeze-card-call tc)
      (= (card-status (unfreeze-card-call-card tc)) card-frozen))))

; Rule: r_62388353e025  |  Line: 3
; NL: "Every call to unfreeze a card is not permitted if the affected account has at least one active restriction of type FRAUD_HOLD."
(assert (forall ((tc ToolCall))
  (=> (and (is-unfreeze-card-call tc)
           (exists ((r Restriction))
             (and (= (restriction-account r) (card-account (unfreeze-card-call-card tc)))
                  (= (is-active-restriction r) true)
                  (= (restriction-type r) fraud-hold))))
      (not (is-permitted tc)))))

; Rule: r_0983f46e1e30  |  Line: 4
; NL: "Every call to unfreeze a card is not permitted if the affected account has at least one active restriction of type AML_REVIEW."
(assert (forall ((tc ToolCall))
  (=> (and (is-unfreeze-card-call tc)
           (exists ((r Restriction))
             (and (= (restriction-account r) (card-account (unfreeze-card-call-card tc)))
                  (= (is-active-restriction r) true)
                  (= (restriction-type r) aml-review))))
      (not (is-permitted tc)))))

; Rule: r_f35e1699c50e  |  Line: 5
; NL: "Every call to unfreeze a card is not permitted if the affected account has at least one active restriction of type SANCTIONS_BLOCK."
(assert (forall ((tc ToolCall))
  (=> (and (is-unfreeze-card-call tc)
           (exists ((r Restriction))
             (and (= (restriction-account r) (card-account (unfreeze-card-call-card tc)))
                  (= (is-active-restriction r) true)
                  (= (restriction-type r) sanctions-block))))
      (not (is-permitted tc)))))

; Rule: r_bf3096098692  |  Line: 6
; NL: "Every call to unfreeze a card is not permitted if the affected account has at least one active restriction of type COURT_ORDER."
(assert (forall ((tc ToolCall))
  (=> (and (is-unfreeze-card-call tc)
           (exists ((r Restriction))
             (and (= (restriction-account r) (card-account (unfreeze-card-call-card tc)))
                  (= (is-active-restriction r) true)
                  (= (restriction-type r) court-order))))
      (not (is-permitted tc)))))

; Rule: r_695263d36286  |  Line: 7
; NL: "Every call to apply an account restriction requires that the target account exists."
(assert (forall ((tc ToolCall))
  (=> (is-apply-restriction-call tc)
      (= (account-exists-in-db (apply-restriction-call-account tc)) true))))

; Rule: r_81411f137148  |  Line: 8
; NL: "Every call to apply an account restriction of type AML_REVIEW requires at least one human approval."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-restriction-call tc)
           (= (apply-restriction-call-type tc) aml-review))
      (= (requires-human-approval tc) true))))

; Rule: r_c5f1cf51b7a0  |  Line: 9
; NL: "Every call to apply an account restriction of type SANCTIONS_BLOCK requires at least one human approval."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-restriction-call tc)
           (= (apply-restriction-call-type tc) sanctions-block))
      (= (requires-human-approval tc) true))))

; Rule: r_ddddabecd8dd  |  Line: 10
; NL: "Every call to apply an account restriction of type COURT_ORDER requires at least one human approval."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-restriction-call tc)
           (= (apply-restriction-call-type tc) court-order))
      (= (requires-human-approval tc) true))))

; ============================================================
; Bundle: nlchunksmt_20260430_222740Z_c50c26a7  |  Committed: 2026-04-30T22:28:39Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_222740Z_c50c26a7 ---
(declare-fun is-lift-restriction-call (ToolCall) Bool)
(declare-fun lift-restriction-call-restriction (ToolCall) Restriction)
(declare-fun restriction-exists-in-db (Restriction) Bool)

(declare-fun is-report-fraud-call (ToolCall) Bool)
(declare-fun report-fraud-call-customer (ToolCall) Customer)
(declare-fun report-fraud-call-references-transaction (ToolCall Transaction) Bool)

(declare-datatype FraudType ((app-fraud) (card-fraud)))
(declare-fun report-fraud-call-type (ToolCall) FraudType)

(declare-fun has-card-identifier (Transaction) Bool)

; Rule: r_ce60bb4702b8  |  Line: 0
; NL: "A call to apply an account restriction of type CUSTOMER_REQUESTED is permitted without further conditions if the target account exists."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-restriction-call tc)
           (= (apply-restriction-call-type tc) customer-requested)
           (= (account-exists-in-db (apply-restriction-call-account tc)) true))
      (= (is-permitted tc) true))))

; Rule: r_871c1ea7063e  |  Line: 1
; NL: "A call to lift an account restriction requires that the target restriction exists."
(assert (forall ((tc ToolCall))
  (=> (is-lift-restriction-call tc)
      (= (restriction-exists-in-db (lift-restriction-call-restriction tc)) true))))

; Rule: r_5a0872c6d186  |  Line: 2
; NL: "A call to lift an account restriction requires that the target restriction is currently active."
(assert (forall ((tc ToolCall))
  (=> (is-lift-restriction-call tc)
      (= (is-active-restriction (lift-restriction-call-restriction tc)) true))))

; Rule: r_2040c62e0376  |  Line: 3
; NL: "A call to lift an account restriction is not permitted if the target restriction has its requires-human-to-lift flag set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-lift-restriction-call tc)
           (= (human-action-required (lift-restriction-call-restriction tc)) true))
      (not (is-permitted tc)))))

; Rule: r_78576ed5c389  |  Line: 4
; NL: "A call to lift an account restriction of type AML_REVIEW requires human approval regardless of the target restriction's requires-human-to-lift flag."
(assert (forall ((tc ToolCall))
  (=> (and (is-lift-restriction-call tc)
           (= (restriction-type (lift-restriction-call-restriction tc)) aml-review))
      (= (requires-human-approval tc) true))))

; Rule: r_6a79ef724206  |  Line: 5
; NL: "A call to lift an account restriction of type SANCTIONS_BLOCK requires human approval regardless of the target restriction's requires-human-to-lift flag."
(assert (forall ((tc ToolCall))
  (=> (and (is-lift-restriction-call tc)
           (= (restriction-type (lift-restriction-call-restriction tc)) sanctions-block))
      (= (requires-human-approval tc) true))))

; Rule: r_046e9f3745a8  |  Line: 6
; NL: "A call to lift an account restriction of type COURT_ORDER is not permitted under any circumstances."
(assert (forall ((tc ToolCall))
  (=> (and (is-lift-restriction-call tc)
           (= (restriction-type (lift-restriction-call-restriction tc)) court-order))
      (not (is-permitted tc)))))

; Rule: r_e8f9279fb9e3  |  Line: 7
; NL: "A call to report fraud requires that the referenced customer exists."
(assert (forall ((tc ToolCall))
  (=> (is-report-fraud-call tc)
      (= (customer-exists-in-db (report-fraud-call-customer tc)) true))))

; Rule: r_8a0dd531e863  |  Line: 8
; NL: "A call to report fraud requires that every referenced transaction exists."
(assert (forall ((tc ToolCall) (t Transaction))
  (=> (and (is-report-fraud-call tc)
           (report-fraud-call-references-transaction tc t))
      (= (transaction-exists-in-db t) true))))

; Rule: r_02fe838e77d3  |  Line: 9
; NL: "A call to report fraud requires that every referenced transaction belongs to the referenced customer."
(assert (forall ((tc ToolCall) (t Transaction))
  (=> (and (is-report-fraud-call tc)
           (report-fraud-call-references-transaction tc t))
      (= (account-owner (transaction-account t)) (report-fraud-call-customer tc)))))

; Rule: r_fe2bcbe9ea81  |  Line: 10
; NL: "A call to report fraud of type APP_FRAUD requires that at least one referenced transaction has a status of POSTED."
(assert (forall ((tc ToolCall))
  (=> (and (is-report-fraud-call tc)
           (= (report-fraud-call-type tc) app-fraud))
      (exists ((t Transaction))
        (and (report-fraud-call-references-transaction tc t)
             (= (transaction-status t) txn-posted))))))

; Rule: r_6de819cd83ef  |  Line: 11
; NL: "A call to report fraud of type CARD_FRAUD requires that at least one referenced transaction has a card identifier."
(assert (forall ((tc ToolCall))
  (=> (and (is-report-fraud-call tc)
           (= (report-fraud-call-type tc) card-fraud))
      (exists ((t Transaction))
        (and (report-fraud-call-references-transaction tc t)
             (= (has-card-identifier t) true))))))

; ============================================================
; Bundle: nlchunksmt_20260430_222902Z_d422a4af  |  Committed: 2026-04-30T22:31:08Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_222902Z_d422a4af ---
(declare-fun is-account-takeover (ToolCall) Bool)
(declare-fun is-identity-theft (ToolCall) Bool)
(declare-fun fraud-report-references-transaction (FraudReport Transaction) Bool)
; Canonical FraudReport denotation for policy rules keyed on FraudReport vs tool-call reference (CHANGELOG R19).
(declare-fun policy-fraud-report-for-call (ToolCall) FraudReport)
(assert (forall ((tc ToolCall) (t Transaction))
  (=> (and (is-report-fraud-call tc) (report-fraud-call-references-transaction tc t))
      (fraud-report-references-transaction (policy-fraud-report-for-call tc) t))))

(declare-datatype MessageCategory ((promotional) (collections)))
(declare-fun is-send-message-call (ToolCall) Bool)
(declare-fun message-call-category (ToolCall) MessageCategory)
(declare-fun message-call-recipient (ToolCall) Customer)

(declare-fun is-escalate-call (ToolCall) Bool)
(declare-fun escalate-call-customer (ToolCall) Customer)

(declare-fun is-log-assessment-call (ToolCall) Bool)
(declare-fun log-assessment-call-customer (ToolCall) Customer)
(declare-fun interaction-exists-in-db (Interaction) Bool)

; Rule: r_b15be43d8644  |  Line: 0
; NL: "A call to report fraud of type ACCOUNT_TAKEOVER requires that the current interaction's has-been-escalated flag is set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-report-fraud-call tc) (= (is-account-takeover tc) true))
      (= (has-been-escalated current-interaction) true))))

; Rule: r_19ccdac5510f  |  Line: 1
; NL: "A call to report fraud of type IDENTITY_THEFT requires that the current interaction's has-been-escalated flag is set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-report-fraud-call tc) (= (is-identity-theft tc) true))
      (= (has-been-escalated current-interaction) true))))

; Rule: r_3b11b659d726  |  Line: 2
; NL: "A call to apply a refund of type DISPUTE_REFUND is not permitted if a fraud report with status CONFIRMED references the transaction associated with the refund."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (refund-call-type tc) dispute-refund)
           (exists ((fr FraudReport))
             (and (= (fraud-report-status fr) fraud-confirmed)
                  (= (fraud-report-references-transaction fr (refund-call-transaction tc)) true))))
      (not (is-permitted tc)))))

; Rule: r_38aab03a57e3  |  Line: 3
; NL: "A call to initiate a dispute is not permitted if a fraud report with status CONFIRMED references the transaction associated with the dispute."
(assert (forall ((tc ToolCall))
  (=> (and (is-initiate-dispute-call tc)
           (exists ((fr FraudReport))
             (and (= (fraud-report-status fr) fraud-confirmed)
                  (= (fraud-report-references-transaction fr (dispute-call-transaction tc)) true))))
      (not (is-permitted tc)))))

; Rule: r_83b4f844bdc4  |  Line: 4
; NL: "A call to apply any refund affecting a customer with a vulnerable flag set to true is not permitted unless a consumer duty assessment for the current interaction has its fair-value-check-passed flag set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (is-vulnerable (refund-call-customer tc)) true)
           (not (exists ((cda ConsumerDutyAssessment))
                  (and (= (assessment-interaction cda) current-interaction)
                       (= (fair-value-check-passed cda) true)))))
      (not (is-permitted tc)))))

; Rule: r_e7047e739cf0  |  Line: 5
; NL: "A call to apply any goodwill credit affecting a customer with a vulnerable flag set to true is not permitted unless a consumer duty assessment for the current interaction has its fair-value-check-passed flag set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (refund-call-type tc) goodwill-credit)
           (= (is-vulnerable (refund-call-customer tc)) true)
           (not (exists ((cda ConsumerDutyAssessment))
                  (and (= (assessment-interaction cda) current-interaction)
                       (= (fair-value-check-passed cda) true)))))
      (not (is-permitted tc)))))

; Rule: r_524e4d13f251  |  Line: 6
; NL: "A call to send a customer message of category PROMOTIONAL is not permitted if the recipient customer has a vulnerable flag set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-send-message-call tc)
           (= (message-call-category tc) promotional)
           (= (is-vulnerable (message-call-recipient tc)) true))
      (not (is-permitted tc)))))

; Rule: r_2c02804c23bd  |  Line: 7
; NL: "A call to send a customer message of category COLLECTIONS is not permitted if the recipient customer has a vulnerable flag set to true, unless the current interaction's has-been-escalated flag is set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-send-message-call tc)
           (= (message-call-category tc) collections)
           (= (is-vulnerable (message-call-recipient tc)) true)
           (not (= (has-been-escalated current-interaction) true)))
      (not (is-permitted tc)))))

; Rule: r_e0111253af77  |  Line: 8
; NL: "If the customer exists, then a call to escalate to a human is permitted."
(assert (forall ((tc ToolCall))
  (=> (and (is-escalate-call tc)
           (= (customer-exists-in-db (escalate-call-customer tc)) true))
      (= (is-permitted tc) true))))

; Rule: r_8a511b3baa4b  |  Line: 9
; NL: "A call to log a consumer duty assessment requires that the customer exists."
(assert (forall ((tc ToolCall))
  (=> (is-log-assessment-call tc)
      (= (customer-exists-in-db (log-assessment-call-customer tc)) true))))

; Rule: r_4f8269c6088a  |  Line: 10
; NL: "A call to log a consumer duty assessment requires that the current interaction exists."
(assert (forall ((tc ToolCall))
  (=> (is-log-assessment-call tc)
      (= (interaction-exists-in-db current-interaction) true))))

; Rule: r_1f0b53bd2d73  |  Line: 11
; NL: "A call to apply any refund of an amount exceeding 20,000 pence to a customer with a vulnerable flag set to true requires that a consumer duty assessment exists for the current interaction with both of its checks passed."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (> (refund-call-amount-pence tc) 20000)
           (= (is-vulnerable (refund-call-customer tc)) true))
      (exists ((cda ConsumerDutyAssessment))
        (and (= (assessment-interaction cda) current-interaction)
             (= (fair-value-check-passed cda) true)
             (= (clear-communication-check-passed cda) true))))))

; ============================================================
; Bundle: nlchunksmt_20260430_223130Z_2b1dc680  |  Committed: 2026-04-30T22:32:36Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_223130Z_2b1dc680 ---
(declare-fun is-request-doc-call (ToolCall) Bool)
(declare-fun request-doc-call-customer (ToolCall) Customer)
(declare-fun request-doc-call-deadline (ToolCall) Int)

(declare-datatype DocType ((proof-of-address) (other-doc)))
(declare-fun request-doc-call-type (ToolCall) DocType)

(declare-fun has-affected-account (ToolCall) Bool)
(declare-fun affected-account (ToolCall) Account)

(declare-fun has-affected-customer (ToolCall) Bool)
(declare-fun affected-customer (ToolCall) Customer)

(declare-fun modifies-financial-state (ToolCall) Bool)
(declare-fun references-missing-entity (ToolCall) Bool)
(declare-fun has-out-of-bounds-numeric-parameter (ToolCall) Bool)

; Rule: r_0bc42110d6de  |  Line: 0
; NL: "Every call to request documentation requires that the associated customer exists."
(assert (forall ((tc ToolCall))
  (=> (is-request-doc-call tc)
      (= (customer-exists-in-db (request-doc-call-customer tc)) true))))

; Rule: r_58f0124d6586  |  Line: 1
; NL: "A call to request documentation with a deadline business days field of less than three is not permitted unless the associated customer's has previously failed documentation request flag is set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-request-doc-call tc)
           (< (request-doc-call-deadline tc) 3)
           (not (= (has-previously-failed-doc-request (request-doc-call-customer tc)) true)))
      (not (is-permitted tc)))))

; Rule: r_c6d6d1eb0b6c  |  Line: 2
; NL: "A call to request documentation of type PROOF_OF_ADDRESS is not permitted if the associated customer's KYC status is VERIFIED, unless an active restriction of type COMPLIANCE_REVIEW is present for that customer."
(assert (forall ((tc ToolCall))
  (=> (and (is-request-doc-call tc)
           (= (request-doc-call-type tc) proof-of-address)
           (= (kyc-status (request-doc-call-customer tc)) verified)
           (not (exists ((r Restriction) (a Account))
                  (and (= (restriction-account r) a)
                       (= (account-owner a) (request-doc-call-customer tc))
                       (= (is-active-restriction r) true)
                       (= (restriction-type r) compliance-review)))))
      (not (is-permitted tc)))))

; Rule: r_d3ed126316a9  |  Line: 3
; NL: "A call of any write type is not permitted if the affected account's status is CLOSED."
(assert (forall ((tc ToolCall))
  (=> (and (is-write-tool-call tc)
           (has-affected-account tc)
           (= (account-status (affected-account tc)) closed))
      (not (is-permitted tc)))))

; Rule: r_54e1cf7cffc3  |  Line: 4
; NL: "A call of any write type other than escalate to human is not permitted if the affected customer's sanctions flag is set to true."
(assert (forall ((tc ToolCall))
  (=> (and (is-write-tool-call tc)
           (not (is-escalate-call tc))
           (has-affected-customer tc)
           (= (has-sanctions (affected-customer tc)) true))
      (not (is-permitted tc)))))

; Rule: r_f8b74f4e3b46  |  Line: 5
; NL: "Every call of any write type that modifies financial state requires that the affected account's status is ACTIVE or RESTRICTED."
(assert (forall ((tc ToolCall))
  (=> (and (is-write-tool-call tc)
           (modifies-financial-state tc)
           (has-affected-account tc))
      (or (= (account-status (affected-account tc)) active)
          (= (account-status (affected-account tc)) restricted)))))

; Rule: r_eaacc5506e85  |  Line: 6
; NL: "A call of any write type other than escalate to human and other than send customer message is not permitted if the affected customer's KYC status is FAILED."
(assert (forall ((tc ToolCall))
  (=> (and (is-write-tool-call tc)
           (not (is-escalate-call tc))
           (not (is-send-message-call tc))
           (has-affected-customer tc)
           (= (kyc-status (affected-customer tc)) failed))
      (not (is-permitted tc)))))

; Rule: r_b0d2123b2e88  |  Line: 7
; NL: "A call to apply any refund is not permitted if the affected account's status is FROZEN, unless the refund is the result of an APPROVED dispute."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (account-status (refund-call-account tc)) frozen)
           (not (exists ((d Dispute))
                  (and (= (dispute-transaction d) (refund-call-transaction tc))
                       (= (dispute-status d) dispute-approved)))))
      (not (is-permitted tc)))))

; Rule: r_1ab7e1f78363  |  Line: 8
; NL: "A call to apply any goodwill credit is not permitted if the affected account's status is FROZEN, unless the goodwill credit is the result of an APPROVED dispute."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (= (refund-call-type tc) goodwill-credit)
           (= (account-status (refund-call-account tc)) frozen)
           (not (exists ((d Dispute))
                  (and (= (dispute-transaction d) (refund-call-transaction tc))
                       (= (dispute-status d) dispute-approved)))))
      (not (is-permitted tc)))))

; Rule: r_7d2fe316f3f4  |  Line: 9
; NL: "A tool call carrying any parameter that references an entity not present in the database is not permitted."
(assert (forall ((tc ToolCall))
  (=> (references-missing-entity tc)
      (not (is-permitted tc)))))

; Rule: r_9d2a3dae1f9a  |  Line: 10
; NL: "A tool call carrying a numeric parameter outside the declared bounds for that parameter is not permitted."
(assert (forall ((tc ToolCall))
  (=> (has-out-of-bounds-numeric-parameter tc)
      (not (is-permitted tc)))))

; ============================================================
; Bundle: nlchunksmt_20260430_223844Z_32cf349d  |  Committed: 2026-04-30T22:39:14Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_223844Z_32cf349d ---
(declare-fun is-duplicate-of-prior-allowed-call-in-interaction (ToolCall) Bool)

; Rule: r_457ca0a03af0  |  Line: 0
; NL: "Every tool call carries a field named 'is duplicate of prior allowed call in interaction', which is a boolean maintained by the runtime."
(assert (forall ((tc ToolCall))
  (or (= (is-duplicate-of-prior-allowed-call-in-interaction tc) true)
      (= (is-duplicate-of-prior-allowed-call-in-interaction tc) false))))

; Rule: r_b5fb85596707  |  Line: 1
; NL: "A tool call is not permitted if its 'is duplicate of prior allowed call in interaction' field is set to true."
(assert (forall ((tc ToolCall))
  (=> (= (is-duplicate-of-prior-allowed-call-in-interaction tc) true)
      (not (is-permitted tc)))))

; ============================================================
; REFINEMENT BATCH: snapshot wiring (CHANGELOG R20) — affected-account / customer / financial flag
; When the discriminating is-*-call is true, runtime snapshots must agree for global write rules (r_d3ed…–r_eaacc…).
; modifies-financial-state is conservative: only refund and lift-restriction.
; ============================================================
(assert (forall ((tc ToolCall))
  (=> (is-apply-refund-call tc)
      (and (has-affected-account tc)
           (= (affected-account tc) (refund-call-account tc))
           (has-affected-customer tc)
           (= (affected-customer tc) (refund-call-customer tc))
           (modifies-financial-state tc)))))

(assert (forall ((tc ToolCall))
  (=> (is-initiate-dispute-call tc)
      (and (has-affected-account tc)
           (= (affected-account tc) (transaction-account (dispute-call-transaction tc)))
           (has-affected-customer tc)
           (= (affected-customer tc) (dispute-call-customer tc))))))

(assert (forall ((tc ToolCall))
  (=> (is-cancel-dispute-call tc)
      (let ((d (cancel-dispute-call-dispute tc)))
        (and (has-affected-account tc)
             (= (affected-account tc) (transaction-account (dispute-transaction d)))
             (has-affected-customer tc)
             (= (affected-customer tc) (account-owner (transaction-account (dispute-transaction d)))))))))

(assert (forall ((tc ToolCall))
  (=> (is-freeze-card-call tc)
      (let ((card (freeze-card-call-card tc)))
        (and (has-affected-account tc)
             (= (affected-account tc) (card-account card))
             (has-affected-customer tc)
             (= (affected-customer tc) (account-owner (card-account card))))))))

(assert (forall ((tc ToolCall))
  (=> (is-unfreeze-card-call tc)
      (let ((card (unfreeze-card-call-card tc)))
        (and (has-affected-account tc)
             (= (affected-account tc) (card-account card))
             (has-affected-customer tc)
             (= (affected-customer tc) (account-owner (card-account card))))))))

(assert (forall ((tc ToolCall))
  (=> (is-apply-restriction-call tc)
      (let ((acc (apply-restriction-call-account tc)))
        (and (has-affected-account tc)
             (= (affected-account tc) acc)
             (has-affected-customer tc)
             (= (affected-customer tc) (account-owner acc)))))))

(assert (forall ((tc ToolCall))
  (=> (is-lift-restriction-call tc)
      (let ((r (lift-restriction-call-restriction tc)))
        (and (has-affected-account tc)
             (= (affected-account tc) (restriction-account r))
             (has-affected-customer tc)
             (= (affected-customer tc) (account-owner (restriction-account r)))
             (modifies-financial-state tc))))))

(assert (forall ((tc ToolCall))
  (=> (is-report-fraud-call tc)
      (and (has-affected-customer tc)
           (= (affected-customer tc) (report-fraud-call-customer tc))))))

(assert (forall ((tc ToolCall))
  (=> (is-send-message-call tc)
      (and (has-affected-customer tc)
           (= (affected-customer tc) (message-call-recipient tc))))))

(assert (forall ((tc ToolCall))
  (=> (is-escalate-call tc)
      (and (has-affected-customer tc)
           (= (affected-customer tc) (escalate-call-customer tc))))))

(assert (forall ((tc ToolCall))
  (=> (is-log-assessment-call tc)
      (and (has-affected-customer tc)
           (= (affected-customer tc) (log-assessment-call-customer tc))))))

(assert (forall ((tc ToolCall))
  (=> (is-request-doc-call tc)
      (and (has-affected-customer tc)
           (= (affected-customer tc) (request-doc-call-customer tc))))))