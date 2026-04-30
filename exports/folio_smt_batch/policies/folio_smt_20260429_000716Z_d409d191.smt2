; ============================================================
; Bundle: folio_smt_20260429_000716Z_d409d191  |  Committed: 2026-04-29T00:07:35Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle folio_smt_20260429_000716Z_d409d191 ---
(declare-sort Employee 0)
(declare-fun schedules-meeting-with-customers (Employee) Bool)
(declare-fun appears-at-company-today (Employee) Bool)
(declare-fun has-lunch-at-company (Employee) Bool)
(declare-fun has-lunch-at-home (Employee) Bool)
(declare-fun works-remotely-from-home (Employee) Bool)
(declare-fun is-in-another-country (Employee) Bool)
(declare-fun is-manager (Employee) Bool)
(declare-const james Employee)

; Rule: r_135ce4e244db  |  Line: 0
; NL: "For every employee: if that employee schedules a meeting with their customers, then that employee appears at the company today."
(assert (forall ((e Employee))
  (=> (schedules-meeting-with-customers e) (appears-at-company-today e))))

; Rule: r_012a29769598  |  Line: 1
; NL: "For every employee: if that employee has lunch at the company, then that employee schedules a meeting with their customers."
(assert (forall ((e Employee))
  (=> (has-lunch-at-company e) (schedules-meeting-with-customers e))))

; Rule: r_7c277c1eef24  |  Line: 2
; NL: "For every employee: that employee has lunch at the company or that employee has lunch at home."
(assert (forall ((e Employee))
  (or (has-lunch-at-company e) (has-lunch-at-home e))))

; Rule: r_079ec071d21e  |  Line: 3
; NL: "If an employee has lunch at home, then that employee works remotely from home."
(assert (forall ((e Employee))
  (=> (has-lunch-at-home e) (works-remotely-from-home e))))

; Rule: r_3ae83a46b8ee  |  Line: 4
; NL: "For every employee: if that employee is in another country, then that employee works remotely from home."
(assert (forall ((e Employee))
  (=> (is-in-another-country e) (works-remotely-from-home e))))

; Rule: r_e54a4cfd575f  |  Line: 5
; NL: "For every manager: it is not the case that that manager works remotely from home."
(assert (forall ((e Employee))
  (=> (is-manager e) (not (works-remotely-from-home e)))))

; Rule: r_1c86b5254467  |  Line: 6
; NL: "James is either both a manager and appears at the company today, or James is neither a manager nor appears at the company today."
(assert (or (and (is-manager james) (appears-at-company-today james))
            (and (not (is-manager james)) (not (appears-at-company-today james)))))

; Rule: r_970cf0d36522  |  Line: 7
; NL: "James does not have lunch at the company."
(assert (not (has-lunch-at-company james)))