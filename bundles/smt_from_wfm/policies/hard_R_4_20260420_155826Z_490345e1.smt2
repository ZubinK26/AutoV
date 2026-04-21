; ============================================================
; Bundle: hard_R_4_20260420_155826Z_490345e1  |  Committed: 2026-04-20T17:11:57Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle hard_R_4_20260420_155826Z_490345e1 ---
(declare-sort Aircraft 0)
(declare-const bluewing-441 Aircraft)
(declare-fun flight-hours-since-heavy-maintenance (Aircraft) Int)
(declare-fun sensor-drift-events-count-last-12m (Aircraft) Int)
(declare-fun has-partial-pitot-static-checks (Aircraft) Bool)
(declare-fun has-full-pitot-static-verification (Aircraft) Bool)
(declare-fun is-grounded (Aircraft) Bool)
(declare-fun air-data-system-checks-passed (Aircraft) Bool)
(declare-fun pitot-static-checks-passed (Aircraft) Bool)
(declare-fun has-signed-maintenance-releases (Aircraft) Bool)

; Rule: r_23dfec745a31  |  Line: 2
; NL: "Bluewing 441 is an aircraft that has accumulated 71,000 flight hours since its last heavy maintenance."
(assert (= (flight-hours-since-heavy-maintenance bluewing-441) 71000))

; Rule: r_9d290076538a  |  Line: 3
; NL: "Bluewing 441 has four independent sensor drift events logged for the same air data computer chain in the last 12 months."
(assert (= (sensor-drift-events-count-last-12m bluewing-441) 4))

; Rule: r_b15a6a60d435  |  Line: 4
; NL: "The maintenance records for Bluewing 441 show only partial pitot-static checks."
(assert (has-partial-pitot-static-checks bluewing-441))

; Rule: r_4296c0b10fcc  |  Line: 5
; NL: "The maintenance records for Bluewing 441 do not show the completion of the full required pitot-static verification package since its last heavy maintenance."
(assert (not (has-full-pitot-static-verification bluewing-441)))

; Rule: r_15dd32ddb34e  |  Line: 6
; NL: "Bluewing 441 is grounded until the air data system checks pass with signed maintenance releases."
(assert (=> (not (and (air-data-system-checks-passed bluewing-441) (has-signed-maintenance-releases bluewing-441)))
            (is-grounded bluewing-441)))

; Rule: r_3f52dbb5ac65  |  Line: 7
; NL: "Bluewing 441 is grounded until the pitot-static checks pass with signed maintenance releases."
(assert (=> (not (and (pitot-static-checks-passed bluewing-441) (has-signed-maintenance-releases bluewing-441)))
            (is-grounded bluewing-441)))