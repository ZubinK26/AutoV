; ============================================================
; Bundle: folio_smt_20260429_000654Z_429a7260  |  Committed: 2026-04-29T00:07:16Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle folio_smt_20260429_000654Z_429a7260 ---
(declare-sort Employee 0)
(declare-fun schedules-meeting-with-customers (Employee) Bool)
(declare-fun appears-in-company-today (Employee) Bool)
(declare-fun has-lunch-in-company (Employee) Bool)
(declare-fun has-lunch-at-home (Employee) Bool)
(declare-fun works-remotely-from-home (Employee) Bool)
(declare-fun is-in-another-country (Employee) Bool)
(declare-fun is-manager (Employee) Bool)
(declare-const james Employee)

; Rule: r_8996512c67da  |  Line: 0
; NL: "For every employee: if that employee schedules a meeting with their customers, then that employee appears in the company today."
(assert (forall ((e Employee))
  (=> (schedules-meeting-with-customers e) (appears-in-company-today e))))

; Rule: r_557f16cdf347  |  Line: 1
; NL: "For every employee: if that employee has lunch in the company, then that employee schedules a meeting with their customers."
(assert (forall ((e Employee))
  (=> (has-lunch-in-company e) (schedules-meeting-with-customers e))))

; Rule: r_ea8f298df9df  |  Line: 2
; NL: "For every employee: that employee has lunch in the company or that employee has lunch at home."
(assert (forall ((e Employee))
  (or (has-lunch-in-company e) (has-lunch-at-home e))))

; Rule: r_abebab46e9ae  |  Line: 3
; NL: "For every employee: it is not the case that (that employee has lunch in the company and that employee has lunch at home)."
(assert (forall ((e Employee))
  (not (and (has-lunch-in-company e) (has-lunch-at-home e)))))

; Rule: r_8c5a56f2f569  |  Line: 4
; NL: "If an employee has lunch at home, then that employee works remotely from home."
(assert (forall ((e Employee))
  (=> (has-lunch-at-home e) (works-remotely-from-home e))))

; Rule: r_44fd4e2a52a3  |  Line: 5
; NL: "For every employee: if that employee is in another country, then that employee works remotely from home."
(assert (forall ((e Employee))
  (=> (is-in-another-country e) (works-remotely-from-home e))))

; Rule: r_f561ed45deec  |  Line: 6
; NL: "For every manager: it is not the case that that manager works remotely from home."
(assert (forall ((e Employee))
  (=> (is-manager e) (not (works-remotely-from-home e)))))

; Rule: r_3986b3ec6a77  |  Line: 7
; NL: "If James is a manager, then James appears in the company today."
(assert (=> (is-manager james) (appears-in-company-today james)))

; Rule: r_74945a96b06b  |  Line: 8
; NL: "If James appears in the company today, then James is a manager."
(assert (=> (appears-in-company-today james) (is-manager james)))

; Rule: r_b081ab4801fb  |  Line: 9
; NL: "James has lunch in the company."
(assert (has-lunch-in-company james))