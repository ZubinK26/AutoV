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