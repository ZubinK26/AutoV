; ============================================================
; Bundle: nlchunksmt_20260430_214111Z_4a941dcb  |  Committed: 2026-04-30T21:41:58Z
; ============================================================
(set-logic ALL)
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

; Rule: r_e8f2c899205b  |  Line: 6
; NL: "Every transaction has exactly one amount in pence."
(assert (forall ((t Transaction))
  (= (transaction-amount-pence t) (transaction-amount-pence t))))

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

; Rule: r_6b6f82808a95  |  Line: 10
; NL: "Every transaction has exactly one field named days since posted."
(assert (forall ((t Transaction))
  (= (days-since-posted t) (days-since-posted t))))

; Rule: r_9209435c4276  |  Line: 11
; NL: "The field named days since posted of every transaction is a non-negative integer maintained by the runtime."
(assert (forall ((t Transaction))
  (>= (days-since-posted t) 0)))

; Rule: r_1aa2ea99aa9d  |  Line: 12
; NL: "Every transaction has exactly one field named has duplicate candidate within window."
(assert (forall ((t Transaction))
  (or (= (has-duplicate-candidate-within-window t) true)
      (= (has-duplicate-candidate-within-window t) false))))

; Rule: r_821b9946980e  |  Line: 13
; NL: "The field named has duplicate candidate within window of every transaction is a boolean maintained by the runtime."
(assert (forall ((t Transaction))
  (or (= (has-duplicate-candidate-within-window t) true)
      (= (has-duplicate-candidate-within-window t) false))))

; Rule: r_44bed1337363  |  Line: 14
; NL: "Every transaction has exactly one section seventy five eligibility flag that is either true or false."
(assert (forall ((t Transaction))
  (or (= (is-section-75-eligible t) true)
      (= (is-section-75-eligible t) false))))

; Rule: r_ff0b24be07d3  |  Line: 15
; NL: "Every transaction has exactly one chargeback window in days."
(assert (forall ((t Transaction))
  (= (chargeback-window-days t) (chargeback-window-days t))))

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

; Rule: r_47f5c56afea2  |  Line: 1
; NL: "The field named fee already reversed of a transaction is a boolean maintained by the runtime."
(assert (forall ((t Transaction))
  (or (= (fee-already-reversed t) true)
      (= (fee-already-reversed t) false))))

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

; Rule: r_25453c863569  |  Line: 7
; NL: "Every refund has exactly one amount in pence."
(assert (forall ((r Refund))
  (= (refund-amount-pence r) (refund-amount-pence r))))

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

; Rule: r_d4479aac5056  |  Line: 14
; NL: "Every call to apply a refund of any type with an amount greater than the original transaction amount is not permitted."
(assert (forall ((tc ToolCall))
  (=> (and (is-apply-refund-call tc)
           (> (refund-call-amount-pence tc) (transaction-amount-pence (refund-call-transaction tc))))
      (not (is-permitted tc)))))

; ============================================================
; Bundle: nlchunksmt_20260430_222310Z_6dfadb65  |  Committed: 2026-04-30T22:24:20Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260430_222310Z_6dfadb65 ---
(declare-fun restriction-account (Restriction) Account)
(declare-fun is-active-restriction (Restriction) Bool)
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

; Rule: r_6f4f6048a1e2  |  Line: 12
; NL: "Every call to initiate a dispute requires that no other open dispute exists for the referenced transaction."
(assert (forall ((tc ToolCall))
  (=> (is-initiate-dispute-call tc)
      (not (exists ((d Dispute))
             (and (= (dispute-transaction d) (dispute-call-transaction tc))
                  (= (dispute-status d) dispute-open)))))))

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

; Rule: r_35c9c9c33202  |  Line: 1
; NL: "Every call to initiate a dispute of type SECTION_75 requires that the referenced transaction amount is at least ten thousand pence."
(assert (forall ((tc ToolCall))
  (=> (and (is-initiate-dispute-call tc) (= (dispute-call-type tc) section-75))
      (>= (transaction-amount-pence (dispute-call-transaction tc)) 10000))))

; Rule: r_5331803ca11a  |  Line: 2
; NL: "Every call to initiate a dispute of type SECTION_75 requires that the referenced transaction amount is at most thirty million pence."
(assert (forall ((tc ToolCall))
  (=> (and (is-initiate-dispute-call tc) (= (dispute-call-type tc) section-75))
      (<= (transaction-amount-pence (dispute-call-transaction tc)) 30000000))))

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