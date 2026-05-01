; ============================================================
; policy_model_refined_simpl.smt2
; ------------------------------------------------------------
; Source NL: agentsim_simplified/04_agentic_guardrails_simpl.md
; Basis:     policy_snapshots/policy_latest.smt2 (chunk bundles preserved below)
;
; REFINEMENTS (this file only; do not edit policy_latest.smt2):
; R-A  Drop standalone ToolCall sort/axioms (refund-only slice; avoids vacuous
;      forall over ToolCall unrelated to is-permitted).
; R-B  Replace tautological "exists Customer/Account/Transaction" axioms with
;      runtime exists-in-db predicates + blocking implications (semantic "DB").
; R-C  Replace universal POSTED on refund-transaction with: if txn is in DB and
;      not POSTED, not permitted (allows grounding PENDING without theory UNSAT).
; R-D  Add cross-entity wiring when entities exist (customer owns account; txn
;      posts to refund account). Translator must still ground consistently.
; R-E  Add explicit Boolean totality for exists-in-db predicates.
; R-F  Add positive completion: when all NL preconditions hold and no block
;      condition applies, is-permitted is true (reduces ambiguous ALLOW path for
;      validator entailment checks).
; ============================================================
(set-logic ALL)

; --- Sorts & datatypes (unchanged from chunk bundle ff3bbd29) ---
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

; REFINEMENT R-B: runtime database presence (ground per entity in scenarios)
(declare-fun customer-exists-in-db (Customer) Bool)
(declare-fun account-exists-in-db (Account) Bool)
(declare-fun transaction-exists-in-db (Transaction) Bool)

; --- Refund call accessors & permission (from chunk 89350534; ToolCall removed R-A) ---
(declare-fun refund-customer (RefundCall) Customer)
(declare-fun refund-account (RefundCall) Account)
(declare-fun refund-transaction (RefundCall) Transaction)
(declare-fun is-permitted (RefundCall) Bool)

; ========== Structural axioms (verbatim intent from policy_latest) ==========

; Rule: r_59fe7b6b17e7
(assert (forall ((c1 Customer) (c2 Customer))
  (=> (= (customer-id c1) (customer-id c2)) (= c1 c2))))

; Rule: r_48e26d26cf87
(assert (forall ((c Customer))
  (or (= (kyc-status c) verified) (= (kyc-status c) failed))))

; Rule: r_e2eec76003b1
(assert (forall ((c Customer))
  (or (= (is-vulnerable c) true) (= (is-vulnerable c) false))))

; Rule: r_76ee120b0cad
(assert (forall ((c Customer))
  (>= (recent-goodwill-credit-total c) 0)))

; Rule: r_0209e93c35d4
(assert (forall ((a1 Account) (a2 Account))
  (=> (= (account-id a1) (account-id a2)) (= a1 a2))))

; Rule: r_f8c1deade931
(assert (forall ((a Account))
  (exists ((c Customer)) (= (account-customer a) c))))

; Rule: r_92ef27ddbee5
(assert (forall ((a Account))
  (or (= (has-sanctions-block a) true) (= (has-sanctions-block a) false))))

; Rule: r_4158290ca8ca
(assert (forall ((t1 Transaction) (t2 Transaction))
  (=> (= (transaction-id t1) (transaction-id t2)) (= t1 t2))))

; Rule: r_fac2b369b33c
(assert (forall ((t Transaction))
  (exists ((a Account)) (= (transaction-account t) a))))

; Rule: r_b9bd888bfad8
(assert (forall ((t Transaction))
  (> (transaction-amount t) 0)))

; Rule: r_363b69bf31e1
(assert (forall ((t Transaction))
  (or (= (transaction-status t) posted) (= (transaction-status t) pending))))

; Rule: r_336e88af5452
(assert (forall ((r RefundCall))
  (or (= (refund-type r) merchant-refund) (= (refund-type r) goodwill-credit))))

; Rule: r_d3b847db68f9
(assert (forall ((r RefundCall))
  (> (refund-amount r) 0)))

; ========== REFINEMENT R-E: totality on DB flags ==========
(assert (forall ((c Customer))
  (or (= (customer-exists-in-db c) true) (= (customer-exists-in-db c) false))))
(assert (forall ((a Account))
  (or (= (account-exists-in-db a) true) (= (account-exists-in-db a) false))))
(assert (forall ((t Transaction))
  (or (= (transaction-exists-in-db t) true) (= (transaction-exists-in-db t) false))))

; ========== REFINEMENT R-D: wiring when entities are present in DB ==========
(assert (forall ((r RefundCall))
  (=> (and (= (customer-exists-in-db (refund-customer r)) true)
           (= (account-exists-in-db (refund-account r)) true))
      (= (account-customer (refund-account r)) (refund-customer r)))))
(assert (forall ((r RefundCall))
  (=> (and (= (account-exists-in-db (refund-account r)) true)
           (= (transaction-exists-in-db (refund-transaction r)) true))
      (= (transaction-account (refund-transaction r)) (refund-account r)))))

; ========== REFINEMENT R-B: missing entity blocks permission ==========
; Replaces chunk rules r_d2019a0b3f74, r_4950ba1a4905, r_a9e3045ec2fc
(assert (forall ((r RefundCall))
  (=> (not (= (customer-exists-in-db (refund-customer r)) true))
      (not (is-permitted r)))))
(assert (forall ((r RefundCall))
  (=> (not (= (account-exists-in-db (refund-account r)) true))
      (not (is-permitted r)))))
(assert (forall ((r RefundCall))
  (=> (not (= (transaction-exists-in-db (refund-transaction r)) true))
      (not (is-permitted r)))))

; ========== REFINEMENT R-C: POSTED requirement (conditional, not universal) ==========
; Replaces chunk rule r_b6d8a9204126 universal equality on status
(assert (forall ((r RefundCall))
  (=> (and (= (transaction-exists-in-db (refund-transaction r)) true)
           (not (= (transaction-status (refund-transaction r)) posted)))
      (not (is-permitted r)))))

; ========== Blocking rules (aligned with NL; same as policy_latest) ==========

; Rule: r_4f623ee23ed9 — FAILED KYC
(assert (forall ((r RefundCall))
  (=> (= (kyc-status (refund-customer r)) failed)
      (not (is-permitted r)))))

; Rule: r_f2adbd257e64 — sanctions
(assert (forall ((r RefundCall))
  (=> (= (has-sanctions-block (refund-account r)) true)
      (not (is-permitted r)))))

; Rule: r_fdd5f30e1dbf — merchant amount > txn
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type r) merchant-refund)
           (> (refund-amount r) (transaction-amount (refund-transaction r))))
      (not (is-permitted r)))))

; Rule: r_d17c2d7b1ff7 — goodwill > 10000
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type r) goodwill-credit)
           (> (refund-amount r) 10000))
      (not (is-permitted r)))))

; Rule: r_f11d5fb27486 — rolling goodwill cap
(assert (forall ((r RefundCall))
  (=> (and (= (refund-type r) goodwill-credit)
           (> (+ (recent-goodwill-credit-total (refund-customer r)) (refund-amount r)) 50000))
      (not (is-permitted r)))))

; Rule: r_e19456715334 — vulnerable & amount > 20000
(assert (forall ((r RefundCall))
  (=> (and (= (is-vulnerable (refund-customer r)) true)
           (> (refund-amount r) 20000))
      (not (is-permitted r)))))

; ========== REFINEMENT R-F: positive permission when all NL gates pass ==========
(assert (forall ((r RefundCall))
  (=> (and
        (= (customer-exists-in-db (refund-customer r)) true)
        (= (account-exists-in-db (refund-account r)) true)
        (= (transaction-exists-in-db (refund-transaction r)) true)
        (= (account-customer (refund-account r)) (refund-customer r))
        (= (transaction-account (refund-transaction r)) (refund-account r))
        (= (transaction-status (refund-transaction r)) posted)
        (= (kyc-status (refund-customer r)) verified)
        (= (has-sanctions-block (refund-account r)) false)
        (=> (= (refund-type r) merchant-refund)
            (<= (refund-amount r) (transaction-amount (refund-transaction r))))
        (=> (= (refund-type r) goodwill-credit)
            (and (<= (refund-amount r) 10000)
                 (<= (+ (recent-goodwill-credit-total (refund-customer r)) (refund-amount r)) 50000)))
        (=> (= (is-vulnerable (refund-customer r)) true)
            (<= (refund-amount r) 20000)))
      (= (is-permitted r) true))))
