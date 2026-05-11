; ============================================================
; Bundle: nlchunksmt_20260501_021637Z_79a1e147  |  Committed: 2026-05-01T02:17:05Z
; ============================================================
(set-logic ALL)
; --- New declarations for bundle nlchunksmt_20260501_021637Z_79a1e147 ---
(declare-sort Customer 0)
(declare-sort CustomerId 0)
(declare-datatype KycStatus ((verified) (failed)))

(declare-fun customer-id-of (Customer) CustomerId)
(declare-fun kyc-status-of (Customer) KycStatus)

; Rule: r_adbe5530bd0a  |  Line: 0
; NL: "Every customer is identified by exactly one unique customer identifier."
(assert (forall ((c1 Customer) (c2 Customer))
  (=> (= (customer-id-of c1) (customer-id-of c2))
      (= c1 c2))))

; Rule: r_00a44cb73cd2  |  Line: 1
; NL: "Every customer has exactly one KYC status that is either VERIFIED or FAILED."
(assert (forall ((c Customer))
  (or (= (kyc-status-of c) verified)
      (= (kyc-status-of c) failed))))

; ============================================================
; Bundle: nlchunksmt_20260501_021705Z_397418b3  |  Committed: 2026-05-01T02:17:27Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_021705Z_397418b3 ---
(declare-fun is-vulnerable (Customer) Bool)

; Rule: r_2fca558f7b77  |  Line: 0
; NL: "Every customer has exactly one vulnerable flag that is either true or false."
(assert (forall ((c Customer))
  (or (= (is-vulnerable c) true)
      (= (is-vulnerable c) false))))

; ============================================================
; Bundle: nlchunksmt_20260501_021727Z_fb2d0b05  |  Committed: 2026-05-01T02:17:57Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_021727Z_fb2d0b05 ---
(declare-fun recent-goodwill-credit-total (Customer) Int)

; Rule: r_e9430c5ec915  |  Line: 0
; NL: "Every customer has exactly one field named recent goodwill credit total."
(assert (forall ((c Customer))
  (= (recent-goodwill-credit-total c) (recent-goodwill-credit-total c))))

; Rule: r_6fd2dc0aa489  |  Line: 1
; NL: "The recent goodwill credit total field is a non-negative amount in pence."
(assert (forall ((c Customer))
  (>= (recent-goodwill-credit-total c) 0)))

; ============================================================
; Bundle: nlchunksmt_20260501_021757Z_f68e62f3  |  Committed: 2026-05-01T02:18:21Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_021757Z_f68e62f3 ---
(declare-sort Account 0)
(declare-sort AccountId 0)
(declare-fun account-id-of (Account) AccountId)
(declare-fun belongs-to (Account) Customer)

; Rule: r_d8e2082ed069  |  Line: 0
; NL: "Every account is identified by exactly one unique account identifier."
(assert (forall ((a1 Account) (a2 Account))
  (=> (= (account-id-of a1) (account-id-of a2))
      (= a1 a2))))

; Rule: r_970349c26849  |  Line: 1
; NL: "Every account belongs to exactly one customer."
(assert (forall ((a Account))
  (= (belongs-to a) (belongs-to a))))

; ============================================================
; Bundle: nlchunksmt_20260501_021822Z_aaf5dbf1  |  Committed: 2026-05-01T02:18:47Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_021822Z_aaf5dbf1 ---
(declare-fun has-sanctions-block (Account) Bool)

; Rule: r_ddba2ceee20c  |  Line: 0
; NL: "Every account has exactly one flag named 'has sanctions block' whose value is exactly one of: true, false."
(assert (forall ((a Account))
  (or (= (has-sanctions-block a) true)
      (= (has-sanctions-block a) false))))

; ============================================================
; Bundle: nlchunksmt_20260501_021848Z_bd99df71  |  Committed: 2026-05-01T02:19:20Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_021848Z_bd99df71 ---
(declare-sort Transaction 0)
(declare-sort TransactionId 0)
(declare-fun transaction-id-of (Transaction) TransactionId)
(declare-fun transaction-account (Transaction) Account)

; Rule: r_4d30368caa0c  |  Line: 0
; NL: "Every transaction is identified by exactly one unique transaction identifier."
(assert (forall ((t1 Transaction) (t2 Transaction))
  (=> (= (transaction-id-of t1) (transaction-id-of t2))
      (= t1 t2))))

; Rule: r_ff6b97c621f0  |  Line: 1
; NL: "Every transaction belongs to exactly one account."
(assert (forall ((t Transaction))
  (= (transaction-account t) (transaction-account t))))

; ============================================================
; Bundle: nlchunksmt_20260501_021921Z_148c8fac  |  Committed: 2026-05-01T02:19:43Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_021921Z_148c8fac ---
(declare-fun transaction-amount-pence (Transaction) Int)

; Rule: r_c2ef950d9f83  |  Line: 0
; NL: "Every transaction has exactly one amount in pence."
(assert (forall ((t Transaction))
  (= (transaction-amount-pence t) (transaction-amount-pence t))))

; Rule: r_0376dcd1972a  |  Line: 1
; NL: "Every transaction's amount in pence is a positive integer."
(assert (forall ((t Transaction))
  (> (transaction-amount-pence t) 0)))

; ============================================================
; Bundle: nlchunksmt_20260501_021943Z_efc9f902  |  Committed: 2026-05-01T02:20:07Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_021943Z_efc9f902 ---
(declare-datatype TransactionStatus ((posted) (pending)))
(declare-fun transaction-status (Transaction) TransactionStatus)

; Rule: r_f0f0f7172c25  |  Line: 0
; NL: "Every transaction has exactly one status."
(assert (forall ((t Transaction))
  (= (transaction-status t) (transaction-status t))))

; Rule: r_e20041dafacb  |  Line: 1
; NL: "The status of every transaction is either POSTED or PENDING."
(assert (forall ((t Transaction))
  (or (= (transaction-status t) posted)
      (= (transaction-status t) pending))))

; ============================================================
; Bundle: nlchunksmt_20260501_022008Z_61c3182a  |  Committed: 2026-05-01T02:20:29Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_022008Z_61c3182a ---
(declare-sort RefundCall 0)
(declare-datatype RefundType ((merchant-refund) (goodwill-credit)))
(declare-fun refund-type-of (RefundCall) RefundType)

; Rule: r_16a609902fa3  |  Line: 0
; NL: "Every refund call has exactly one refund type that is one of MERCHANT_REFUND or GOODWILL_CREDIT."
(assert (forall ((r RefundCall))
  (or (= (refund-type-of r) merchant-refund)
      (= (refund-type-of r) goodwill-credit))))

; ============================================================
; Bundle: nlchunksmt_20260501_022030Z_c0f3f15d  |  Committed: 2026-05-01T02:20:56Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_022030Z_c0f3f15d ---
(declare-fun refund-amount-pence (RefundCall) Int)

; Rule: r_68914cdf2b11  |  Line: 0
; NL: "Every refund call has exactly one amount in pence."
(assert (forall ((r RefundCall))
  (= (refund-amount-pence r) (refund-amount-pence r))))

; Rule: r_18f0f85ff573  |  Line: 1
; NL: "The amount in pence of a refund call is a positive integer."
(assert (forall ((r RefundCall))
  (> (refund-amount-pence r) 0)))

; ============================================================
; Bundle: nlchunksmt_20260501_022056Z_0bfbc8ec  |  Committed: 2026-05-01T02:21:21Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_022056Z_0bfbc8ec ---
(declare-sort ToolCall 0)
(declare-fun is-write-tool-call (ToolCall) Bool)
(declare-fun has-typed-parameters (ToolCall) Bool)

; Rule: r_18aa443c73b5  |  Line: 0
; NL: "Every tool call is one of the defined write tool calls."
(assert (forall ((t ToolCall))
  (is-write-tool-call t)))

; Rule: r_519fd4bd865b  |  Line: 1
; NL: "Every tool call carries typed parameters."
(assert (forall ((t ToolCall))
  (has-typed-parameters t)))

; ============================================================
; Bundle: nlchunksmt_20260501_022121Z_6101f429  |  Committed: 2026-05-01T02:21:41Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_022121Z_6101f429 ---
(declare-fun affected-customer (RefundCall) Customer)
(declare-fun exists-in-database (Customer) Bool)

; Rule: r_21457572b4ae  |  Line: 0
; NL: "Every call to apply a refund of any type requires that the affected customer exists in the database."
(assert (forall ((r RefundCall))
  (exists-in-database (affected-customer r))))

; ============================================================
; Bundle: nlchunksmt_20260501_022142Z_d8a8684e  |  Committed: 2026-05-01T02:22:04Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_022142Z_d8a8684e ---
(declare-fun affected-account (RefundCall) Account)
(declare-fun account-exists-in-database (Account) Bool)

; Rule: r_aa6947bbde75  |  Line: 0
; NL: "Every call to apply a refund of any type requires that the account affected by the refund exists in the database."
(assert (forall ((r RefundCall))
  (account-exists-in-database (affected-account r))))

; ============================================================
; Bundle: nlchunksmt_20260501_022204Z_4f44dbb3  |  Committed: 2026-05-01T02:22:23Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_022204Z_4f44dbb3 ---
(declare-fun referenced-transaction (RefundCall) Transaction)
(declare-fun transaction-exists-in-database (Transaction) Bool)

; Rule: r_175d168f362f  |  Line: 0
; NL: "Every call to apply a refund of any type requires that the referenced transaction exists in the database."
(assert (forall ((r RefundCall))
  (transaction-exists-in-database (referenced-transaction r))))

; ============================================================
; Bundle: nlchunksmt_20260501_022223Z_77885540  |  Committed: 2026-05-01T02:22:43Z
; ============================================================
; Rule: r_a1258f399729  |  Line: 0
; NL: "Every call to apply a refund of any type requires that the referenced transaction has the status POSTED."
(assert (forall ((r RefundCall))
  (= (transaction-status (referenced-transaction r)) posted)))

; ============================================================
; Bundle: nlchunksmt_20260501_022244Z_80e1ef02  |  Committed: 2026-05-01T02:23:05Z
; ============================================================
; --- New declarations for bundle nlchunksmt_20260501_022244Z_80e1ef02 ---
(declare-fun is-permitted (RefundCall) Bool)

; Rule: r_43510f8010f5  |  Line: 0
; NL: "If a customer's KYC status is FAILED, a call to apply a refund of any type for that customer is not permitted."
(assert (forall ((r RefundCall))
  (=> (= (kyc-status-of (affected-customer r)) failed)
      (not (is-permitted r)))))

; ============================================================
; Bundle: nlchunksmt_20260501_022306Z_cb2a86b3  |  Committed: 2026-05-01T02:23:26Z
; ============================================================
; Rule: r_01b5e839091e  |  Line: 0
; NL: "A call to apply a refund of any type is not permitted if the affected account has its sanctions block flag set to true."
(assert (forall ((r RefundCall))
  (=> (= (has-sanctions-block (affected-account r)) true)
      (not (is-permitted r)))))

; ============================================================
; Bundle: nlchunksmt_20260501_022327Z_6eaf4f4f  |  Committed: 2026-05-01T02:23:51Z
; ============================================================
; Rule: r_7d08afd9ad76  |  Line: 0
; NL: "A call to apply a refund of type MERCHANT_REFUND is not permitted if the refund's amount is greater than the referenced transaction's amount."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type-of r) merchant-refund)
           (> (refund-amount-pence r) (transaction-amount-pence (referenced-transaction r))))
      (not (is-permitted r)))))

; ============================================================
; Bundle: nlchunksmt_20260501_022351Z_5ba3fc15  |  Committed: 2026-05-01T02:24:13Z
; ============================================================
; Rule: r_e8ea435b3b78  |  Line: 0
; NL: "Any call to apply a refund of type GOODWILL_CREDIT with an amount greater than ten thousand pence is not permitted."
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type-of r) goodwill-credit)
           (> (refund-amount-pence r) 10000))
      (not (is-permitted r)))))