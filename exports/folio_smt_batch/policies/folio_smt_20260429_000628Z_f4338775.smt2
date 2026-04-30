; ============================================================
; Bundle: folio_smt_20260429_000628Z_f4338775  |  Committed: 2026-04-29T00:06:54Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle folio_smt_20260429_000628Z_f4338775 ---
(declare-sort Person 0)
(declare-fun chaperones-high-school-dances (Person) Bool)
(declare-fun is-student-who-attends-school (Person) Bool)
(declare-fun is-young-child-or-teenager-wishing-to-further-career (Person) Bool)
(declare-fun attends-school-events (Person) Bool)
(declare-fun is-very-engaged-with-school-events (Person) Bool)
(declare-const bonnie Person)

; Rule: r_978d61cdbf5e  |  Line: 3
; NL: "Every person who chaperones high school dances is not a student who attends the school."
(assert (forall ((p Person))
  (=> (chaperones-high-school-dances p)
      (not (is-student-who-attends-school p)))))

; Rule: r_76f5fca5d9ec  |  Line: 5
; NL: "Every person who is a young child or teenager who wishes to further their academic career and educational opportunities is a student who attends the school."
(assert (forall ((p Person))
  (=> (is-young-child-or-teenager-wishing-to-further-career p)
      (is-student-who-attends-school p))))

; Rule: r_bc4673042a1f  |  Line: 6
; NL: "If Bonnie attends school events and Bonnie is very engaged with school events, then Bonnie is a student who attends the school."
(assert (=> (and (attends-school-events bonnie) (is-very-engaged-with-school-events bonnie))
            (is-student-who-attends-school bonnie)))

; Rule: r_d3c0bf792ab2  |  Line: 7
; NL: "If Bonnie is a student who attends the school, then Bonnie attends school events and Bonnie is very engaged with school events."
(assert (=> (is-student-who-attends-school bonnie)
            (and (attends-school-events bonnie) (is-very-engaged-with-school-events bonnie))))

; Rule: r_62d04de58172  |  Line: 8
; NL: "If Bonnie chaperones high school dances, then Bonnie is a young child or teenager who wishes to further her academic career and educational opportunities."
(assert (=> (chaperones-high-school-dances bonnie)
            (is-young-child-or-teenager-wishing-to-further-career bonnie)))