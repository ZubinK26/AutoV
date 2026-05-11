; ============================================================
; Bundle: nlchunksmt_20260501_003654Z_ff3bbd29  |  Committed: 2026-05-01T03:26:15Z
; ============================================================
(set-logic ALL)
; --- New declarations for bundle nlchunksmt_20260501_003654Z_ff3bbd29 ---
(declare-sort Customer 0)
(declare-sort CustomerIdentifier 0)
(declare-fun customer-id (Customer) CustomerIdentifier)

(declare-datatype KycStatus ((verified) (failed)))
(declare-fun kyc-status (Customer) KycStatus)

(declare-fun is-vulnerable (Customer) Bool)

(declare-fun recent-goodwill-credit-total (Customer) Int)

(declare-sort Account 0)
(declare-sort AccountIdentifier 0)
(declare-fun account-id (Account) AccountIdentifier)

(declare-fun account-owner (Account) Customer)

(declare-fun has-sanctions-block (Account) Bool)

(declare-sort Transaction 0)
(declare-sort TransactionIdentifier 0)
(declare-fun transaction-id (Transaction) TransactionIdentifier)

(declare-fun transaction-account (Transaction) Account)

(declare-fun transaction-amount (Transaction) Int)

(declare-datatype TransactionStatus ((posted) (pending)))
(declare-fun transaction-status (Transaction) TransactionStatus)

(declare-sort RefundCall 0)
(declare-datatype RefundType ((merchant-refund) (goodwill-credit)))
(declare-fun refund-type (RefundCall) RefundType)

(declare-fun refund-amount (RefundCall) Int)

; Rule: r_4297fe6a43a9  |  Line: 0
; NL: "Every customer is identified by a unique customer identifier."
(assert (forall ((c1 Customer) (c2 Customer))
  (=> (= (customer-id c1) (customer-id c2)) (= c1 c2))))

; Rule: r_2c23b6d893f2  |  Line: 1
; NL: "Every customer has a KYC status that is either VERIFIED or FAILED."
(assert (forall ((c Customer))
  (or (= (kyc-status c) verified) (= (kyc-status c) failed))))

; Rule: r_7a348b29c016  |  Line: 2
; NL: "Every customer has a vulnerable flag that is either true or false."
(assert (forall ((c Customer))
  (or (= (is-vulnerable c) true) (= (is-vulnerable c) false))))

; Rule: r_ae5775a4bca8  |  Line: 3
; NL: "Every customer has a field named recent goodwill credit total, which is a non-negative amount in pence maintained by the runtime."
(assert (forall ((c Customer))
  (>= (recent-goodwill-credit-total c) 0)))

; Rule: r_d653563d9fea  |  Line: 4
; NL: "Every account is identified by a unique account identifier."
(assert (forall ((a1 Account) (a2 Account))
  (=> (= (account-id a1) (account-id a2)) (= a1 a2))))

; Rule: r_ad57449e5e81  |  Line: 5
; NL: "Every account belongs to exactly one customer."
(assert (forall ((a Account))
  (= (account-owner a) (account-owner a))))

; Rule: r_b3fd3b69f55a  |  Line: 6
; NL: "Every account has a flag named has sanctions block, which is either true or false."
(assert (forall ((a Account))
  (or (= (has-sanctions-block a) true) (= (has-sanctions-block a) false))))

; Rule: r_12f5ca84defe  |  Line: 7
; NL: "Every transaction is identified by a unique transaction identifier."
(assert (forall ((t1 Transaction) (t2 Transaction))
  (=> (= (transaction-id t1) (transaction-id t2)) (= t1 t2))))

; Rule: r_adc3aa4896fa  |  Line: 8
; NL: "Every transaction belongs to exactly one account."
(assert (forall ((t Transaction))
  (= (transaction-account t) (transaction-account t))))

; Rule: r_a38af76f9de4  |  Line: 9
; NL: "Every transaction has an amount in pence, which is a positive integer."
(assert (forall ((t Transaction))
  (> (transaction-amount t) 0)))

; Rule: r_efe019fac138  |  Line: 10
; NL: "Every transaction has a status that is either POSTED or PENDING."
(assert (forall ((t Transaction))
  (or (= (transaction-status t) posted) (= (transaction-status t) pending))))

; Rule: r_a43128590a3d  |  Line: 11
; NL: "Every refund call has a refund type that is either MERCHANT_REFUND or GOODWILL_CREDIT."
(assert (forall ((r RefundCall))
  (or (= (refund-type r) merchant-refund) (= (refund-type r) goodwill-credit))))

; Rule: r_3ed79cf59326  |  Line: 12
; NL: "Every refund call has an amount in pence, which is a positive integer."
(assert (forall ((r RefundCall))
  (> (refund-amount r) 0)))

; ============================================================
; Bundle: nlchunksmt_20260501_003911Z_89350534  |  Committed: 2026-05-01T03:26:45Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_003911Z_89350534 ---
(declare-sort ToolCall 0)
(declare-fun is-write-tool-call (ToolCall) Bool)
(declare-fun has-typed-parameters (ToolCall) Bool)

(declare-fun refund-customer (RefundCall) Customer)
(declare-fun customer-exists (Customer) Bool)

(declare-fun refund-account (RefundCall) Account)
(declare-fun account-exists (Account) Bool)

(declare-fun refund-transaction (RefundCall) Transaction)
(declare-fun transaction-exists (Transaction) Bool)

(declare-fun is-permitted (RefundCall) Bool)

; Rule: r_d89ba329c721  |  Line: 0
; NL: "Every tool call is one of the defined write tool calls."
(assert (forall ((t ToolCall))
  (is-write-tool-call t)))

; Rule: r_bc14f3731435  |  Line: 1
; NL: "Every tool call carries typed parameters."
(assert (forall ((t ToolCall))
  (has-typed-parameters t)))

; Rule: r_bce7487ae4b3  |  Line: 2
; NL: "Every call to apply a refund of any type requires that the affected customer exists in the database."
(assert (forall ((r RefundCall))
  (=> (is-permitted r) (customer-exists (refund-customer r)))))

; Rule: r_0af62d410945  |  Line: 3
; NL: "Every call to apply a refund of any type requires that the affected account exists in the database."
(assert (forall ((r RefundCall))
  (=> (is-permitted r) (account-exists (refund-account r)))))

; Rule: r_055c1dd6b72b  |  Line: 4
; NL: "Every call to apply a refund of any type requires that the referenced transaction exists in the database."
(assert (forall ((r RefundCall))
  (=> (is-permitted r) (transaction-exists (refund-transaction r)))))

; Rule: r_07e0f5d78a05  |  Line: 5
; NL: "Every call to apply a refund of any type requires that the referenced transaction has the status POSTED."
(assert (forall ((r RefundCall))
  (=> (is-permitted r) (= (transaction-status (refund-transaction r)) posted))))

; Rule: r_a11cf15ec788  |  Line: 6
; NL: "Any call to apply a refund of any type is not permitted if the affected customer's KYC status is FAILED."
(assert (forall ((r RefundCall))
  (=> (= (kyc-status (refund-customer r)) failed) (not (is-permitted r)))))

; Rule: r_6e221ec5d563  |  Line: 7
; NL: "Any call to apply a refund of any type is not permitted if the affected account has its sanctions block flag set to true."
(assert (forall ((r RefundCall))
  (=> (= (has-sanctions-block (refund-account r)) true) (not (is-permitted r)))))

; Rule: r_431ce57414f1  |  Line: 8
; NL: "Any call to apply a refund of type MERCHANT_REFUND with an amount greater than the referenced transaction's amount is not permitted."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type r) merchant-refund)
           (> (refund-amount r) (transaction-amount (refund-transaction r))))
      (not (is-permitted r)))))

; Rule: r_aadd641e9e4f  |  Line: 9
; NL: "Any call to apply a refund of type GOODWILL_CREDIT with an amount greater than ten thousand pence is not permitted."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type r) goodwill-credit)
           (> (refund-amount r) 10000))
      (not (is-permitted r)))))

; Rule: r_19d089c9c3d8  |  Line: 10
; NL: "Any call to apply a refund of type GOODWILL_CREDIT is not permitted if the sum of the affected customer's recent goodwill credit total and the proposed amount exceeds fifty thousand pence."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type r) goodwill-credit)
           (> (+ (recent-goodwill-credit-total (refund-customer r)) (refund-amount r)) 50000))
      (not (is-permitted r)))))

; ============================================================
; Bundle: nlchunksmt_20260501_004015Z_46b66138  |  Committed: 2026-05-01T03:26:57Z
; ============================================================
; Rule: r_a0d89c22f150  |  Line: 0
; NL: "A call to apply a refund of any type is not permitted if the affected customer's vulnerable flag is set to true and the proposed refund amount exceeds 20,000 pence."
(assert (forall ((r RefundCall))
  (=> (and (= (is-vulnerable (refund-customer r)) true)
           (> (refund-amount r) 20000))
      (not (is-permitted r)))))