; ============================================================
; Bundle: folio_smt_20260429_000601Z_36a22ee5  |  Committed: 2026-04-29T00:06:28Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle folio_smt_20260429_000601Z_36a22ee5 ---
(declare-sort Person 0)
(declare-const bonnie Person)
(declare-fun chaperones-high-school-dances (Person) Bool)
(declare-fun is-student-who-attends-school (Person) Bool)
(declare-fun is-young-child-or-teenager (Person) Bool)
(declare-fun wishes-to-further-academic-career (Person) Bool)
(declare-fun attends-and-is-engaged-with-school-events (Person) Bool)
(declare-fun is-inactive-and-disinterested-member (Person) Bool)

; Rule: r_39552e935dac  |  Line: 3
; NL: "Every person who chaperones high school dances is not a student who attends the school."
(assert (forall ((p Person))
  (=> (chaperones-high-school-dances p)
      (not (is-student-who-attends-school p)))))

; Rule: r_e8a45e9070e7  |  Line: 5
; NL: "Every person who is a young child or teenager and who wishes to further their academic career and educational opportunities is a student who attends the school."
(assert (forall ((p Person))
  (=> (and (is-young-child-or-teenager p)
           (wishes-to-further-academic-career p))
      (is-student-who-attends-school p))))

; Rule: r_8094872e4f03  |  Line: 6
; NL: "Bonnie attends and is very engaged with school events and is a student who attends the school, if and only if Bonnie attends and is very engaged with school events or is a student who attends the school."
(assert (= (and (attends-and-is-engaged-with-school-events bonnie)
                (is-student-who-attends-school bonnie))
           (or (attends-and-is-engaged-with-school-events bonnie)
               (is-student-who-attends-school bonnie))))

; Rule: r_0820b4fba330  |  Line: 7
; NL: "If (Bonnie is a young child or teenager who wishes to further her academic career and educational opportunities and Bonnie chaperones high school dances) or (it is not the case that Bonnie is a young child or teenager who wishes to further her academic career and educational opportunities), then Bonnie is a student who attends the school or Bonnie is an inactive and disinterested member of the community."
(assert (=> (or (and (is-young-child-or-teenager bonnie)
                     (wishes-to-further-academic-career bonnie)
                     (chaperones-high-school-dances bonnie))
                (not (and (is-young-child-or-teenager bonnie)
                          (wishes-to-further-academic-career bonnie))))
            (or (is-student-who-attends-school bonnie)
                (is-inactive-and-disinterested-member bonnie))))