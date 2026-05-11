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