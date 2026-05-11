; ============================================================
; Bundle: nlchunksmt_20260501_003654Z_ff3bbd29  |  Committed: 2026-05-01T14:25:36Z
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
(declare-fun customer-id (Customer) CustomerId)
(declare-fun kyc-status (Customer) KycStatus)
(declare-fun is-vulnerable (Customer) Bool)
(declare-fun recent-goodwill-credit-total (Customer) Int)
(declare-fun account-id (Account) AccountId)
(declare-fun account-owner (Account) Customer)
(declare-fun has-sanctions-block (Account) Bool)
(declare-fun transaction-id (Transaction) TransactionId)
(declare-fun transaction-account (Transaction) Account)
(declare-fun transaction-amount (Transaction) Int)
(declare-fun transaction-status (Transaction) TransactionStatus)
(declare-fun refund-call-type (RefundCall) RefundType)
(declare-fun refund-call-amount (RefundCall) Int)

; Rule: r_8aea31875a9d  |  Line: 0
; NL: "Every customer is identified by a unique customer identifier."
(assert (forall ((c1 Customer) (c2 Customer))
  (=> (= (customer-id c1) (customer-id c2)) (= c1 c2))))

; Rule: r_9da377b531ba  |  Line: 1
; NL: "Every customer has a KYC status that is either VERIFIED or FAILED."
(assert (forall ((c Customer))
  (or (= (kyc-status c) verified)
      (= (kyc-status c) failed))))

; Rule: r_3f2229585844  |  Line: 2
; NL: "Every customer has a vulnerable flag that is either true or false."
(assert (forall ((c Customer))
  (or (= (is-vulnerable c) true)
      (= (is-vulnerable c) false))))

; Rule: r_3126cef7bfef  |  Line: 3
; NL: "Every customer has a field named recent goodwill credit total, which is a non-negative amount in pence maintained by the runtime."
(assert (forall ((c Customer))
  (>= (recent-goodwill-credit-total c) 0)))

; Rule: r_96a057261dd5  |  Line: 4
; NL: "Every account is identified by a unique account identifier."
(assert (forall ((a1 Account) (a2 Account))
  (=> (= (account-id a1) (account-id a2)) (= a1 a2))))

; Rule: r_a6a1176e796b  |  Line: 5
; NL: "Every account belongs to exactly one customer."
(assert (forall ((a Account))
  (exists ((c Customer))
    (and (= (account-owner a) c)
         (forall ((c2 Customer))
           (=> (= (account-owner a) c2) (= c2 c)))))))

; Rule: r_f1ebddd9a87c  |  Line: 6
; NL: "Every account has a flag named has sanctions block, which is either true or false."
(assert (forall ((a Account))
  (or (= (has-sanctions-block a) true)
      (= (has-sanctions-block a) false))))

; Rule: r_907abe9dd4d7  |  Line: 7
; NL: "Every transaction is identified by a unique transaction identifier."
(assert (forall ((t1 Transaction) (t2 Transaction))
  (=> (= (transaction-id t1) (transaction-id t2)) (= t1 t2))))

; Rule: r_2973c7a99c9f  |  Line: 8
; NL: "Every transaction belongs to exactly one account."
(assert (forall ((t Transaction))
  (exists ((a Account))
    (and (= (transaction-account t) a)
         (forall ((a2 Account))
           (=> (= (transaction-account t) a2) (= a2 a)))))))

; Rule: r_43a147a3dc54  |  Line: 9
; NL: "Every transaction has an amount in pence, which is a positive integer."
(assert (forall ((t Transaction))
  (> (transaction-amount t) 0)))

; Rule: r_eebe81cfd635  |  Line: 10
; NL: "Every transaction has a status that is either POSTED or PENDING."
(assert (forall ((t Transaction))
  (or (= (transaction-status t) posted)
      (= (transaction-status t) pending))))

; Rule: r_caaa14b44893  |  Line: 11
; NL: "Every refund call has a refund type that is either MERCHANT_REFUND or GOODWILL_CREDIT."
(assert (forall ((r RefundCall))
  (or (= (refund-call-type r) merchant-refund)
      (= (refund-call-type r) goodwill-credit))))

; Rule: r_8b8279dbebab  |  Line: 12
; NL: "Every refund call has an amount in pence, which is a positive integer."
(assert (forall ((r RefundCall))
  (> (refund-call-amount r) 0)))

; ============================================================
; Bundle: nlchunksmt_20260501_003911Z_89350534  |  Committed: 2026-05-01T14:27:31Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_003911Z_89350534 ---
(declare-sort ToolCall 0)
(declare-sort Parameter 0)
(declare-datatype WriteToolCallType ((apply-refund-call) (other-write-call)))
(declare-fun tool-call-type (ToolCall) WriteToolCallType)
(declare-fun tool-call-parameter (ToolCall Parameter) Bool)
(declare-fun parameter-has-type (Parameter) Bool)
(declare-fun refund-call-customer (RefundCall) Customer)
(declare-fun refund-call-account (RefundCall) Account)
(declare-fun refund-call-transaction (RefundCall) Transaction)
(declare-fun customer-exists-in-db (Customer) Bool)
(declare-fun account-exists-in-db (Account) Bool)
(declare-fun transaction-exists-in-db (Transaction) Bool)
(declare-fun refund-call-is-permitted (RefundCall) Bool)

; Rule: r_2f6017a2efdf  |  Line: 0
; NL: "Every tool call is one of the defined write tool calls."
(assert (forall ((tc ToolCall))
  (or (= (tool-call-type tc) apply-refund-call)
      (= (tool-call-type tc) other-write-call))))

; Rule: r_8bc789d7ce40  |  Line: 1
; NL: "Every tool call carries typed parameters."
(assert (forall ((tc ToolCall) (p Parameter))
  (=> (tool-call-parameter tc p)
      (parameter-has-type p))))
(assert (forall ((tc ToolCall))
  (exists ((p Parameter))
    (tool-call-parameter tc p))))

; Rule: r_c213365d29df  |  Line: 2
; NL: "Every call to apply a refund of any type requires that the affected customer exists in the database."
(assert (forall ((r RefundCall))
  (=> (refund-call-is-permitted r)
      (customer-exists-in-db (refund-call-customer r)))))

; Rule: r_ec75304d0cf1  |  Line: 3
; NL: "Every call to apply a refund of any type requires that the affected account exists in the database."
(assert (forall ((r RefundCall))
  (=> (refund-call-is-permitted r)
      (account-exists-in-db (refund-call-account r)))))

; Rule: r_4daa4a5c4086  |  Line: 4
; NL: "Every call to apply a refund of any type requires that the referenced transaction exists in the database."
(assert (forall ((r RefundCall))
  (=> (refund-call-is-permitted r)
      (transaction-exists-in-db (refund-call-transaction r)))))

; Rule: r_735598283eaf  |  Line: 5
; NL: "Every call to apply a refund of any type requires that the referenced transaction has the status POSTED."
(assert (forall ((r RefundCall))
  (=> (refund-call-is-permitted r)
      (= (transaction-status (refund-call-transaction r)) posted))))

; Rule: r_f0524b87b4f1  |  Line: 6
; NL: "Any call to apply a refund of any type is not permitted if the affected customer's KYC status is FAILED."
(assert (forall ((r RefundCall))
  (=> (= (kyc-status (refund-call-customer r)) failed)
      (not (refund-call-is-permitted r)))))

; Rule: r_785e2bfec884  |  Line: 7
; NL: "Any call to apply a refund of any type is not permitted if the affected account has its sanctions block flag set to true."
(assert (forall ((r RefundCall))
  (=> (has-sanctions-block (refund-call-account r))
      (not (refund-call-is-permitted r)))))

; Rule: r_83a39acdc64a  |  Line: 8
; NL: "Any call to apply a refund of type MERCHANT_REFUND with an amount greater than the referenced transaction's amount is not permitted."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-call-type r) merchant-refund)
           (> (refund-call-amount r) (transaction-amount (refund-call-transaction r))))
      (not (refund-call-is-permitted r)))))

; Rule: r_2be50faf874d  |  Line: 9
; NL: "Any call to apply a refund of type GOODWILL_CREDIT with an amount greater than ten thousand pence is not permitted."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-call-type r) goodwill-credit)
           (> (refund-call-amount r) 10000))
      (not (refund-call-is-permitted r)))))

; Rule: r_1a3ecde44429  |  Line: 10
; NL: "Any call to apply a refund of type GOODWILL_CREDIT is not permitted if the sum of the affected customer's recent goodwill credit total and the proposed amount exceeds fifty thousand pence."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-call-type r) goodwill-credit)
           (> (+ (recent-goodwill-credit-total (refund-call-customer r))
                 (refund-call-amount r))
              50000))
      (not (refund-call-is-permitted r)))))

; ============================================================
; Bundle: nlchunksmt_20260501_004015Z_46b66138  |  Committed: 2026-05-01T14:27:36Z
; ============================================================
; Rule: r_842f59b96669  |  Line: 0
; NL: "A call to apply a refund of any type is not permitted if the affected customer's vulnerable flag is set to true and the proposed refund amount exceeds 20,000 pence."
(assert (forall ((r RefundCall))
  (=> (and (is-vulnerable (refund-call-customer r))
           (> (refund-call-amount r) 20000))
      (not (refund-call-is-permitted r)))))