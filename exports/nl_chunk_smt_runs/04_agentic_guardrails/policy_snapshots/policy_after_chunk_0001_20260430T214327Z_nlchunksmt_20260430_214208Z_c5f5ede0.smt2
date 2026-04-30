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