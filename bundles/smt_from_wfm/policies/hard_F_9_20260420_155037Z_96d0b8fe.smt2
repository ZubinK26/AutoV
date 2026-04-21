; ============================================================
; Bundle: hard_F_9_20260420_155037Z_96d0b8fe  |  Committed: 2026-04-20T17:09:32Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle hard_F_9_20260420_155037Z_96d0b8fe ---
(declare-sort Person 0)
(declare-fun is-grand-slam-champion (Person) Bool)
(declare-fun is-oscar-nominated-actor (Person) Bool)
(declare-fun is-professional-tennis-player (Person) Bool)
(declare-fun is-celebrity (Person) Bool)
(declare-fun is-athlete (Person) Bool)
(declare-fun is-well-paid (Person) Bool)
(declare-fun is-famous (Person) Bool)
(declare-fun lives-in-tax-haven (Person) Bool)
(declare-const djokovic Person)

; Rule: r_2237f4dc684f  |  Line: 0
; NL: "Every person is either a Grand Slam champion or an Oscar-nominated actor."
(assert (forall ((p Person))
  (or (is-grand-slam-champion p)
      (is-oscar-nominated-actor p))))

; Rule: r_a700396f5d4f  |  Line: 1
; NL: "Every person who is a Grand Slam champion is a professional tennis player."
(assert (forall ((p Person))
  (=> (is-grand-slam-champion p)
      (is-professional-tennis-player p))))

; Rule: r_3b9942aa9f06  |  Line: 2
; NL: "Every person who is an Oscar-nominated actor is a celebrity."
(assert (forall ((p Person))
  (=> (is-oscar-nominated-actor p)
      (is-celebrity p))))

; Rule: r_b9ffeebf78d0  |  Line: 3
; NL: "Every professional tennis player is an athlete."
(assert (forall ((p Person))
  (=> (is-professional-tennis-player p)
      (is-athlete p))))

; Rule: r_9f572f854d89  |  Line: 4
; NL: "If a person is a celebrity, then that person is well paid."
(assert (forall ((p Person))
  (=> (is-celebrity p)
      (is-well-paid p))))

; Rule: r_588d843230c0  |  Line: 5
; NL: "If a person is an athlete, then that person is famous."
(assert (forall ((p Person))
  (=> (is-athlete p)
      (is-famous p))))

; Rule: r_4b4bb36b0430  |  Line: 6
; NL: "Every well-paid person lives in a tax haven."
(assert (forall ((p Person))
  (=> (is-well-paid p)
      (lives-in-tax-haven p))))

; Rule: r_9afac405dbaf  |  Line: 7
; NL: "If Djokovic is famous and Djokovic is an athlete, then Djokovic lives in a tax haven."
(assert (=> (and (is-famous djokovic) (is-athlete djokovic))
            (lives-in-tax-haven djokovic)))

; Rule: r_330b8aef0c11  |  Line: 8
; NL: "Djokovic is a Grand Slam champion."
(assert (is-grand-slam-champion djokovic))