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