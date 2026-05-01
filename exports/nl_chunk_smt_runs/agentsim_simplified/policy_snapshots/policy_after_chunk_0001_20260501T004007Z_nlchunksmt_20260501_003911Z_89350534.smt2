; ============================================================
; Bundle: nlchunksmt_20260501_003654Z_ff3bbd29  |  Committed: 2026-05-01T00:37:38Z
; ============================================================
(set-logic ALL)
; --- New declarations for bundle nlchunksmt_20260501_003654Z_ff3bbd29 ---
(declare-sort Customer 0)
(declare-sort CustomerId 0)
(declare-sort Account 0)
(declare-sort AccountId 0)
(declare-sort Transaction 0)
(declare-sort TransactionId 0)
(declare-sort RefundCall 0)

(declare-datatype KycStatus ((verified) (failed)))
(declare-datatype TransactionStatus ((posted) (pending)))
(declare-datatype RefundType ((merchant-refund) (goodwill-credit)))

(declare-fun customer-id (Customer) CustomerId)
(declare-fun kyc-status (Customer) KycStatus)
(declare-fun is-vulnerable (Customer) Bool)
(declare-fun recent-goodwill-credit-total (Customer) Int)

(declare-fun account-id (Account) AccountId)
(declare-fun account-customer (Account) Customer)
(declare-fun has-sanctions-block (Account) Bool)

(declare-fun transaction-id (Transaction) TransactionId)
(declare-fun transaction-account (Transaction) Account)
(declare-fun transaction-amount (Transaction) Int)
(declare-fun transaction-status (Transaction) TransactionStatus)

(declare-fun refund-type (RefundCall) RefundType)
(declare-fun refund-amount (RefundCall) Int)

; Rule: r_59fe7b6b17e7  |  Line: 0
; NL: "Every customer is identified by a unique customer identifier."
(assert (forall ((c1 Customer) (c2 Customer))
  (=> (= (customer-id c1) (customer-id c2)) (= c1 c2))))

; Rule: r_48e26d26cf87  |  Line: 1
; NL: "Every customer has a KYC status that is either VERIFIED or FAILED."
(assert (forall ((c Customer))
  (or (= (kyc-status c) verified) (= (kyc-status c) failed))))

; Rule: r_e2eec76003b1  |  Line: 2
; NL: "Every customer has a vulnerable flag that is either true or false."
(assert (forall ((c Customer))
  (or (= (is-vulnerable c) true) (= (is-vulnerable c) false))))

; Rule: r_76ee120b0cad  |  Line: 3
; NL: "Every customer has a field named recent goodwill credit total, which is a non-negative amount in pence maintained by the runtime."
(assert (forall ((c Customer))
  (>= (recent-goodwill-credit-total c) 0)))

; Rule: r_0209e93c35d4  |  Line: 4
; NL: "Every account is identified by a unique account identifier."
(assert (forall ((a1 Account) (a2 Account))
  (=> (= (account-id a1) (account-id a2)) (= a1 a2))))

; Rule: r_f8c1deade931  |  Line: 5
; NL: "Every account belongs to exactly one customer."
(assert (forall ((a Account))
  (exists ((c Customer)) (= (account-customer a) c))))

; Rule: r_92ef27ddbee5  |  Line: 6
; NL: "Every account has a flag named has sanctions block, which is either true or false."
(assert (forall ((a Account))
  (or (= (has-sanctions-block a) true) (= (has-sanctions-block a) false))))

; Rule: r_4158290ca8ca  |  Line: 7
; NL: "Every transaction is identified by a unique transaction identifier."
(assert (forall ((t1 Transaction) (t2 Transaction))
  (=> (= (transaction-id t1) (transaction-id t2)) (= t1 t2))))

; Rule: r_fac2b369b33c  |  Line: 8
; NL: "Every transaction belongs to exactly one account."
(assert (forall ((t Transaction))
  (exists ((a Account)) (= (transaction-account t) a))))

; Rule: r_b9bd888bfad8  |  Line: 9
; NL: "Every transaction has an amount in pence, which is a positive integer."
(assert (forall ((t Transaction))
  (> (transaction-amount t) 0)))

; Rule: r_363b69bf31e1  |  Line: 10
; NL: "Every transaction has a status that is either POSTED or PENDING."
(assert (forall ((t Transaction))
  (or (= (transaction-status t) posted) (= (transaction-status t) pending))))

; Rule: r_336e88af5452  |  Line: 11
; NL: "Every refund call has a refund type that is either MERCHANT_REFUND or GOODWILL_CREDIT."
(assert (forall ((r RefundCall))
  (or (= (refund-type r) merchant-refund) (= (refund-type r) goodwill-credit))))

; Rule: r_d3b847db68f9  |  Line: 12
; NL: "Every refund call has an amount in pence, which is a positive integer."
(assert (forall ((r RefundCall))
  (> (refund-amount r) 0)))

; ============================================================
; Bundle: nlchunksmt_20260501_003911Z_89350534  |  Committed: 2026-05-01T00:40:07Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_003911Z_89350534 ---
(declare-sort ToolCall 0)
(declare-fun is-defined-write-tool-call (ToolCall) Bool)
(declare-fun has-typed-parameters (ToolCall) Bool)

(declare-fun refund-customer (RefundCall) Customer)
(declare-fun refund-account (RefundCall) Account)
(declare-fun refund-transaction (RefundCall) Transaction)
(declare-fun is-permitted (RefundCall) Bool)

; Rule: r_0b163770060a  |  Line: 0
; NL: "Every tool call is one of the defined write tool calls."
(assert (forall ((t ToolCall))
  (is-defined-write-tool-call t)))

; Rule: r_37a0880ceefa  |  Line: 1
; NL: "Every tool call carries typed parameters."
(assert (forall ((t ToolCall))
  (has-typed-parameters t)))

; Rule: r_d2019a0b3f74  |  Line: 2
; NL: "Every call to apply a refund of any type requires that the affected customer exists in the database."
(assert (forall ((r RefundCall))
  (exists ((c Customer)) (= (refund-customer r) c))))

; Rule: r_4950ba1a4905  |  Line: 3
; NL: "Every call to apply a refund of any type requires that the affected account exists in the database."
(assert (forall ((r RefundCall))
  (exists ((a Account)) (= (refund-account r) a))))

; Rule: r_a9e3045ec2fc  |  Line: 4
; NL: "Every call to apply a refund of any type requires that the referenced transaction exists in the database."
(assert (forall ((r RefundCall))
  (exists ((t Transaction)) (= (refund-transaction r) t))))

; Rule: r_b6d8a9204126  |  Line: 5
; NL: "Every call to apply a refund of any type requires that the referenced transaction has the status POSTED."
(assert (forall ((r RefundCall))
  (= (transaction-status (refund-transaction r)) posted)))

; Rule: r_4f623ee23ed9  |  Line: 6
; NL: "Any call to apply a refund of any type is not permitted if the affected customer's KYC status is FAILED."
(assert (forall ((r RefundCall))
  (=> (= (kyc-status (refund-customer r)) failed)
      (not (is-permitted r)))))

; Rule: r_f2adbd257e64  |  Line: 7
; NL: "Any call to apply a refund of any type is not permitted if the affected account has its sanctions block flag set to true."
(assert (forall ((r RefundCall))
  (=> (= (has-sanctions-block (refund-account r)) true)
      (not (is-permitted r)))))

; Rule: r_fdd5f30e1dbf  |  Line: 8
; NL: "Any call to apply a refund of type MERCHANT_REFUND with an amount greater than the referenced transaction's amount is not permitted."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type r) merchant-refund)
           (> (refund-amount r) (transaction-amount (refund-transaction r))))
      (not (is-permitted r)))))

; Rule: r_d17c2d7b1ff7  |  Line: 9
; NL: "Any call to apply a refund of type GOODWILL_CREDIT with an amount greater than ten thousand pence is not permitted."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type r) goodwill-credit)
           (> (refund-amount r) 10000))
      (not (is-permitted r)))))

; Rule: r_f11d5fb27486  |  Line: 10
; NL: "Any call to apply a refund of type GOODWILL_CREDIT is not permitted if the sum of the affected customer's recent goodwill credit total and the proposed amount exceeds fifty thousand pence."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type r) goodwill-credit)
           (> (+ (recent-goodwill-credit-total (refund-customer r)) (refund-amount r)) 50000))
      (not (is-permitted r)))))