; ============================================================
; Bundle: hard_E_6_20260420_165941Z_09d88cea  |  Committed: 2026-04-20T17:14:26Z
; ============================================================
; --- New declarations for bundle hard_E_6_20260420_165941Z_09d88cea ---
(set-logic ALL)
(declare-sort Book 0)
(declare-sort Member 0)
(declare-fun days-overdue (Book) Int)
(declare-fun borrower-of (Book) Member)
(declare-fun is-library-member (Member) Bool)
(declare-fun accrued-fine (Book) Int)
(declare-fun fine-cap (Member) Int)
(declare-fun enrolled-in-amnesty-weekend (Member) Bool)
(declare-fun is-suspended-from-borrowing (Member) Bool)
(declare-fun account-flagged-for-desk-review (Member) Bool)
(declare-fun is-returned (Book) Bool)
(declare-const riley Member)
(declare-const rileys-book Book)

; Rule: r_a1484978daee  |  Line: 0
; NL: "If a book is more than twenty-one days overdue and the borrower is a library member and the accrued fine exceeds the member’s fine cap and the member has not enrolled in the amnesty weekend, then the member is suspended from borrowing."
(assert (forall ((b Book) (m Member))
  (=> (and (> (days-overdue b) 21)
           (= (borrower-of b) m)
           (is-library-member m)
           (> (accrued-fine b) (fine-cap m))
           (not (enrolled-in-amnesty-weekend m)))
      (is-suspended-from-borrowing m))))

; Rule: r_5e3716d5db53  |  Line: 1
; NL: "If a book is more than twenty-one days overdue and the borrower is a library member and the accrued fine exceeds the member’s fine cap and the member has not enrolled in the amnesty weekend, then the member's account is flagged for desk review."
(assert (forall ((b Book) (m Member))
  (=> (and (> (days-overdue b) 21)
           (= (borrower-of b) m)
           (is-library-member m)
           (> (accrued-fine b) (fine-cap m))
           (not (enrolled-in-amnesty-weekend m)))
      (account-flagged-for-desk-review m))))

; Rule: r_302d6af2b65f  |  Line: 4
; NL: "If a book is more than twenty-one days overdue and the borrower is a library member and the member has enrolled in the amnesty weekend, then the account is not flagged for desk review."
(assert (forall ((b Book) (m Member))
  (=> (and (> (days-overdue b) 21)
           (= (borrower-of b) m)
           (is-library-member m)
           (enrolled-in-amnesty-weekend m))
      (not (account-flagged-for-desk-review m)))))

; Rule: r_4241323464dc  |  Line: 5
; NL: "Riley is a library member."
(assert (is-library-member riley))

; Rule: r_ff29ab8b2e0c  |  Line: 6
; NL: "Riley has a book that is twenty-four days overdue."
(assert (and (= (borrower-of rileys-book) riley)
             (= (days-overdue rileys-book) 24)))

; Rule: r_b7fc57f202e0  |  Line: 7
; NL: "The accrued fine for the book exceeds Riley’s fine cap."
(assert (> (accrued-fine rileys-book) (fine-cap riley)))

; Rule: r_0867e50c325c  |  Line: 8
; NL: "Riley has not enrolled in the amnesty weekend."
(assert (not (enrolled-in-amnesty-weekend riley)))

; Rule: r_50cab413e1be  |  Line: 9
; NL: "The book has not been returned."
(assert (not (is-returned rileys-book)))

; Rule: r_28a7689f1d83  |  Line: 10
; NL: "Riley’s account is flagged for desk review."
(assert (account-flagged-for-desk-review riley))