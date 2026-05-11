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