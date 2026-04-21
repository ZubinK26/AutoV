; ============================================================
; Bundle: hard_E_5_20260420_165746Z_bad4fdc5  |  Committed: 2026-04-20T17:14:07Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle hard_E_5_20260420_165746Z_bad4fdc5 ---
(declare-sort LoanOfficer 0)
(declare-sort Application 0)
(declare-datatype State ((california) (nevada)))
(declare-datatype CensusTractFlag ((infrastructure-incomplete) (none)))
(declare-fun is-licensed-in (LoanOfficer State) Bool)
(declare-fun deals-closed-last-year (LoanOfficer) Int)
(declare-fun borrower-dti (Application) Int)
(declare-fun census-tract-flag (Application) CensusTractFlag)
(declare-fun has-elevated-approval-ceiling (LoanOfficer Application) Bool)
(declare-const jamie LoanOfficer)
(declare-const current-app Application)

; Rule: r_ce15882b2e59  |  Line: 0
; NL: "If a loan officer is licensed in California and the loan officer is licensed in Nevada and the loan officer has closed at least 12 rural-development deals in the last calendar year, then the loan officer has an elevated approval ceiling of $1,200,000 for single-section manufactured housing, unless the borrower’s debt-to-income ratio exceeds 43 percent or the census tract is flagged 'infrastructure incomplete'."
(assert (forall ((lo LoanOfficer) (app Application))
  (=> (and (is-licensed-in lo california)
           (is-licensed-in lo nevada)
           (>= (deals-closed-last-year lo) 12)
           (not (> (borrower-dti app) 43))
           (not (= (census-tract-flag app) infrastructure-incomplete)))
      (has-elevated-approval-ceiling lo app))))

; Rule: r_70db0b2ad18c  |  Line: 1
; NL: "The elevated approval ceiling never applies when the census tract flag is set to 'infrastructure incomplete'."
(assert (forall ((lo LoanOfficer) (app Application))
  (=> (= (census-tract-flag app) infrastructure-incomplete)
      (not (has-elevated-approval-ceiling lo app)))))

; Rule: r_29dfc640fdd8  |  Line: 2
; NL: "Jamie is a loan officer."
; (jamie is declared as a constant of sort LoanOfficer)

; Rule: r_346f534a2de7  |  Line: 3
; NL: "Jamie is licensed in both California and Nevada."
(assert (and (is-licensed-in jamie california) (is-licensed-in jamie nevada)))

; Rule: r_108d98a5e60f  |  Line: 4
; NL: "Jamie closed fifteen rural-development deals in the last calendar year."
(assert (= (deals-closed-last-year jamie) 15))

; Rule: r_396b9bc4e459  |  Line: 5
; NL: "For the current application, the subject census tract is flagged 'infrastructure incomplete'."
(assert (= (census-tract-flag current-app) infrastructure-incomplete))

; Rule: r_c46514741686  |  Line: 6
; NL: "Jamie is not allowed to use the elevated approval ceiling for this application."
(assert (not (has-elevated-approval-ceiling jamie current-app)))