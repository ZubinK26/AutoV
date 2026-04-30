; ============================================================
; Bundle: folio_smt_20260429_000536Z_ea3bfbd5  |  Committed: 2026-04-29T00:06:01Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle folio_smt_20260429_000536Z_ea3bfbd5 ---
(declare-sort Person 0)
(declare-const bonnie Person)
(declare-fun chaperones-high-school-dances (Person) Bool)
(declare-fun is-student-who-attends-school (Person) Bool)
(declare-fun is-young-child (Person) Bool)
(declare-fun is-teenager (Person) Bool)
(declare-fun wishes-to-further-academic-career (Person) Bool)
(declare-fun attends-school-events (Person) Bool)
(declare-fun is-very-engaged-with-school-events (Person) Bool)
(declare-fun performs-in-school-talent-shows-often (Person) Bool)

; Rule: r_50f579727e22  |  Line: 3
; NL: "Every person who chaperones high school dances is not a student who attends the school."
(assert (forall ((p Person))
  (=> (chaperones-high-school-dances p)
      (not (is-student-who-attends-school p)))))

; Rule: r_4a5447bf38f1  |  Line: 5
; NL: "Every person who is a young child or a teenager and who wishes to further their academic career and educational opportunities is a student who attends the school."
(assert (forall ((p Person))
  (=> (and (or (is-young-child p) (is-teenager p))
           (wishes-to-further-academic-career p))
      (is-student-who-attends-school p))))

; Rule: r_305bad64cc15  |  Line: 6
; NL: "Bonnie attends school events and is very engaged with school events and is a student who attends the school, if and only if Bonnie attends school events and is very engaged with school events or is a student who attends the school."
(assert (= (and (attends-school-events bonnie)
                (is-very-engaged-with-school-events bonnie)
                (is-student-who-attends-school bonnie))
           (or (and (attends-school-events bonnie)
                    (is-very-engaged-with-school-events bonnie))
               (is-student-who-attends-school bonnie))))

; Rule: r_8c932d64ab6b  |  Line: 7
; NL: "Bonnie performs in school talent shows often."
(assert (performs-in-school-talent-shows-often bonnie))