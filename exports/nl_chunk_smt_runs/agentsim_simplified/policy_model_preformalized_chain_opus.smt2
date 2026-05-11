; ============================================================
; Bundle: nlchunksmt_20260501_003654Z_ff3bbd29  |  Committed: 2026-05-01T14:37:23Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_003654Z_ff3bbd29 ---
(declare-sort Customer 0)
(declare-sort Account 0)
(declare-sort Transaction 0)
(declare-sort RefundCall 0)
(declare-sort CustomerId 0)
(declare-sort AccountId 0)
(declare-sort TransactionId 0)
(declare-datatype KycStatus ((verified) (failed)))
(declare-datatype TransactionStatus ((posted) (pending)))
(declare-datatype RefundType ((merchant-refund) (goodwill-credit)))
(declare-fun customer-id-of (Customer) CustomerId)
(declare-fun kyc-status-of (Customer) KycStatus)
(declare-fun is-vulnerable (Customer) Bool)
(declare-fun recent-goodwill-credit-total-of (Customer) Int)
(declare-fun account-id-of (Account) AccountId)
(declare-fun customer-of-account (Account) Customer)
(declare-fun has-sanctions-block (Account) Bool)
(declare-fun transaction-id-of (Transaction) TransactionId)
(declare-fun account-of-transaction (Transaction) Account)
(declare-fun amount-of-transaction (Transaction) Int)
(declare-fun status-of-transaction (Transaction) TransactionStatus)
(declare-fun refund-type-of (RefundCall) RefundType)
(declare-fun amount-of-refund-call (RefundCall) Int)

; Rule: r_e3924823a44c  |  Line: 0
; NL: "Every customer is identified by a unique customer identifier."
(assert (forall ((c1 Customer) (c2 Customer))
  (=> (= (customer-id-of c1) (customer-id-of c2)) (= c1 c2))))

; Rule: r_2d084338af19  |  Line: 1
; NL: "Every customer has a KYC status that is either VERIFIED or FAILED."
(assert (forall ((c Customer))
  (or (= (kyc-status-of c) verified)
      (= (kyc-status-of c) failed))))

; Rule: r_804ce4d352f1  |  Line: 2
; NL: "Every customer has a vulnerable flag that is either true or false."
(assert (forall ((c Customer))
  (or (is-vulnerable c) (not (is-vulnerable c)))))

; Rule: r_9f96426dcfe8  |  Line: 3
; NL: "Every customer has a field named recent goodwill credit total, which is a non-negative amount in pence maintained by the runtime."
(assert (forall ((c Customer))
  (>= (recent-goodwill-credit-total-of c) 0)))

; Rule: r_3c5ac69c5469  |  Line: 4
; NL: "Every account is identified by a unique account identifier."
(assert (forall ((a1 Account) (a2 Account))
  (=> (= (account-id-of a1) (account-id-of a2)) (= a1 a2))))

; Rule: r_3da9085a945d  |  Line: 5
; NL: "Every account belongs to exactly one customer."
(assert (forall ((a Account))
  (exists ((c Customer)) (= (customer-of-account a) c))))

; Rule: r_714c27e438c7  |  Line: 6
; NL: "Every account has a flag named has sanctions block, which is either true or false."
(assert (forall ((a Account))
  (or (has-sanctions-block a) (not (has-sanctions-block a)))))

; Rule: r_1030d31ee37d  |  Line: 7
; NL: "Every transaction is identified by a unique transaction identifier."
(assert (forall ((t1 Transaction) (t2 Transaction))
  (=> (= (transaction-id-of t1) (transaction-id-of t2)) (= t1 t2))))

; Rule: r_c9ae62d20e48  |  Line: 8
; NL: "Every transaction belongs to exactly one account."
(assert (forall ((t Transaction))
  (exists ((a Account)) (= (account-of-transaction t) a))))

; Rule: r_c02b12c3f055  |  Line: 9
; NL: "Every transaction has an amount in pence, which is a positive integer."
(assert (forall ((t Transaction))
  (> (amount-of-transaction t) 0)))

; Rule: r_a30092ddead8  |  Line: 10
; NL: "Every transaction has a status that is either POSTED or PENDING."
(assert (forall ((t Transaction))
  (or (= (status-of-transaction t) posted)
      (= (status-of-transaction t) pending))))

; Rule: r_270a1a87ff26  |  Line: 11
; NL: "Every refund call has a refund type that is either MERCHANT_REFUND or GOODWILL_CREDIT."
(assert (forall ((r RefundCall))
  (or (= (refund-type-of r) merchant-refund)
      (= (refund-type-of r) goodwill-credit))))

; Rule: r_9f439192e22f  |  Line: 12
; NL: "Every refund call has an amount in pence, which is a positive integer."
(assert (forall ((r RefundCall))
  (> (amount-of-refund-call r) 0)))

; ============================================================
; Bundle: nlchunksmt_20260501_003911Z_89350534  |  Committed: 2026-05-01T14:37:42Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_003911Z_89350534 ---
(declare-sort ToolCall 0)
(declare-sort Parameter 0)
(declare-sort ParameterType 0)
(declare-datatype WriteToolCallKind ((apply-refund-call)))
(declare-fun kind-of-tool-call (ToolCall) WriteToolCallKind)
(declare-fun parameters-of-tool-call (ToolCall Parameter) Bool)
(declare-fun type-of-parameter (Parameter) ParameterType)
(declare-fun customer-of-refund-call (RefundCall) Customer)
(declare-fun account-of-refund-call (RefundCall) Account)
(declare-fun transaction-of-refund-call (RefundCall) Transaction)
(declare-fun customer-exists-in-db (Customer) Bool)
(declare-fun account-exists-in-db (Account) Bool)
(declare-fun transaction-exists-in-db (Transaction) Bool)
(declare-fun is-permitted (RefundCall) Bool)

; Rule: r_31dd93d1c7a6  |  Line: 0
; NL: "Every tool call is one of the defined write tool calls."
(assert (forall ((tc ToolCall))
  (= (kind-of-tool-call tc) apply-refund-call)))

; Rule: r_58fbc2051f0c  |  Line: 1
; NL: "Every tool call carries typed parameters."
(assert (forall ((tc ToolCall))
  (exists ((p Parameter)) (parameters-of-tool-call tc p))))
(assert (forall ((tc ToolCall) (p Parameter))
  (=> (parameters-of-tool-call tc p)
      (exists ((pt ParameterType)) (= (type-of-parameter p) pt)))))

; Rule: r_16b08a5997dc  |  Line: 2
; NL: "Every call to apply a refund of any type requires that the affected customer exists in the database."
(assert (forall ((r RefundCall))
  (=> (is-permitted r)
      (customer-exists-in-db (customer-of-refund-call r)))))

; Rule: r_ea064eadb6f1  |  Line: 3
; NL: "Every call to apply a refund of any type requires that the affected account exists in the database."
(assert (forall ((r RefundCall))
  (=> (is-permitted r)
      (account-exists-in-db (account-of-refund-call r)))))

; Rule: r_ab1bbf0bf943  |  Line: 4
; NL: "Every call to apply a refund of any type requires that the referenced transaction exists in the database."
(assert (forall ((r RefundCall))
  (=> (is-permitted r)
      (transaction-exists-in-db (transaction-of-refund-call r)))))

; Rule: r_5e17b900fb64  |  Line: 5
; NL: "Every call to apply a refund of any type requires that the referenced transaction has the status POSTED."
(assert (forall ((r RefundCall))
  (=> (is-permitted r)
      (= (status-of-transaction (transaction-of-refund-call r)) posted))))

; Rule: r_21965f2399b0  |  Line: 6
; NL: "Any call to apply a refund of any type is not permitted if the affected customer's KYC status is FAILED."
(assert (forall ((r RefundCall))
  (=> (= (kyc-status-of (customer-of-refund-call r)) failed)
      (not (is-permitted r)))))

; Rule: r_a81f5570c0e0  |  Line: 7
; NL: "Any call to apply a refund of any type is not permitted if the affected account has its sanctions block flag set to true."
(assert (forall ((r RefundCall))
  (=> (has-sanctions-block (account-of-refund-call r))
      (not (is-permitted r)))))

; Rule: r_71697a21b04a  |  Line: 8
; NL: "Any call to apply a refund of type MERCHANT_REFUND with an amount greater than the referenced transaction's amount is not permitted."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type-of r) merchant-refund)
           (> (amount-of-refund-call r)
              (amount-of-transaction (transaction-of-refund-call r))))
      (not (is-permitted r)))))

; Rule: r_5924d6acb8cc  |  Line: 9
; NL: "Any call to apply a refund of type GOODWILL_CREDIT with an amount greater than ten thousand pence is not permitted."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type-of r) goodwill-credit)
           (> (amount-of-refund-call r) 10000))
      (not (is-permitted r)))))

; Rule: r_7bef4d77a49d  |  Line: 10
; NL: "Any call to apply a refund of type GOODWILL_CREDIT is not permitted if the sum of the affected customer's recent goodwill credit total and the proposed amount exceeds fifty thousand pence."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type-of r) goodwill-credit)
           (> (+ (recent-goodwill-credit-total-of (customer-of-refund-call r))
                 (amount-of-refund-call r))
              50000))
      (not (is-permitted r)))))

; ============================================================
; Bundle: nlchunksmt_20260501_004015Z_46b66138  |  Committed: 2026-05-01T14:37:48Z
; ============================================================
; Rule: r_d5547a7aadaa  |  Line: 0
; NL: "A call to apply a refund of any type is not permitted if the affected customer's vulnerable flag is set to true and the proposed refund amount exceeds 20,000 pence."
(assert (forall ((r RefundCall))
  (=> (and (is-vulnerable (customer-of-refund-call r))
           (> (amount-of-refund-call r) 20000))
      (not (is-permitted r)))))