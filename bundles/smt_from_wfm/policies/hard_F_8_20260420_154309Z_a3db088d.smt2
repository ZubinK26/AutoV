; ============================================================
; Bundle: hard_F_8_20260420_154309Z_a3db088d  |  Committed: 2026-04-20T17:09:15Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle hard_F_8_20260420_154309Z_a3db088d ---
(declare-sort Employee 0)
(declare-sort Country 0)
(declare-fun schedules-meeting-with-customers (Employee) Bool)
(declare-fun is-present-at-company-today (Employee) Bool)
(declare-fun has-lunch-at-company (Employee) Bool)
(declare-fun has-lunch-at-home (Employee) Bool)
(declare-fun works-remotely-from-home (Employee) Bool)
(declare-fun country-of (Employee) Country)
(declare-const company-country Country)
(declare-fun is-manager (Employee) Bool)
(declare-const james Employee)

; Rule: r_4227eefdfa2a  |  Line: 0
; NL: "Every employee who schedules at least one meeting with their customers is present at the company today."
(assert (forall ((e Employee))
  (=> (schedules-meeting-with-customers e) (is-present-at-company-today e))))

; Rule: r_702653ddf728  |  Line: 1
; NL: "Every employee who has lunch at the company schedules at least one meeting with their customers."
(assert (forall ((e Employee))
  (=> (has-lunch-at-company e) (schedules-meeting-with-customers e))))

; Rule: r_ef6ca6fc98d7  |  Line: 2
; NL: "Every employee either has lunch at the company or has lunch at home."
(assert (forall ((e Employee))
  (or (has-lunch-at-company e) (has-lunch-at-home e))))

; Rule: r_a563f68900b0  |  Line: 3
; NL: "If an employee has lunch at home, then that employee is working remotely from home."
(assert (forall ((e Employee))
  (=> (has-lunch-at-home e) (works-remotely-from-home e))))

; Rule: r_4506711a4811  |  Line: 4
; NL: "Every employee who is in a country other than the company's country works remotely from home."
(assert (forall ((e Employee))
  (=> (not (= (country-of e) company-country)) (works-remotely-from-home e))))

; Rule: r_c24cbbdc8f59  |  Line: 5
; NL: "No manager works remotely from home."
(assert (forall ((e Employee))
  (=> (is-manager e) (not (works-remotely-from-home e)))))

; Rule: r_6668a3e2ae50  |  Line: 6
; NL: "James is either both a manager and present at the company today, or James is neither a manager nor present at the company today."
(assert (or 
  (and (is-manager james) (is-present-at-company-today james))
  (and (not (is-manager james)) (not (is-present-at-company-today james)))))

; Rule: r_1891b4e2f5d9  |  Line: 7
; NL: "James has lunch at the company."
(assert (has-lunch-at-company james))