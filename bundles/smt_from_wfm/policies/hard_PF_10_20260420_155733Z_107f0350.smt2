; ============================================================
; Bundle: hard_PF_10_20260420_155733Z_107f0350  |  Committed: 2026-04-20T17:11:39Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle hard_PF_10_20260420_155733Z_107f0350 ---
(declare-sort Person 0)
(declare-fun is-man (Person) Bool)
(declare-fun is-taller-than (Person Person) Bool)
(declare-fun is-shorter-than (Person Person) Bool)
(declare-fun can-block-shooting (Person Person) Bool)
(declare-fun is-in-michaels-class (Person) Bool)
(declare-fun jumps-when-shooting (Person) Bool)
(declare-fun is-shooter (Person) Bool)
(declare-fun is-great-shooter (Person) Bool)
(declare-const michael Person)
(declare-const peter Person)
(declare-const windy Person)

; Rule: r_d48f60b5a30f  |  Line: 0
; NL: "For every man x and every man y, if x is taller than y, then x can block the shooting of y."
(assert (forall ((x Person) (y Person))
  (=> (and (is-man x) (is-man y) (is-taller-than x y))
      (can-block-shooting x y))))

; Rule: r_b23b95384403  |  Line: 1
; NL: "Michael is a man."
(assert (is-man michael))

; Rule: r_f037cb034732  |  Line: 2
; NL: "For every person p in Michael's class, if p is not Michael, then Michael is taller than p."
(assert (forall ((p Person))
  (=> (and (is-in-michaels-class p) (not (= p michael)))
      (is-taller-than michael p))))

; Rule: r_92a47c31eb90  |  Line: 3
; NL: "If person x is taller than person y and person y is taller than person z, then person x is taller than person z."
(assert (forall ((x Person) (y Person) (z Person))
  (=> (and (is-taller-than x y) (is-taller-than y z))
      (is-taller-than x z))))

; Rule: r_8be4b6a1d13b  |  Line: 4
; NL: "Peter is a man."
(assert (is-man peter))

; Rule: r_ca1706e36acd  |  Line: 5
; NL: "Peter is taller than Michael."
(assert (is-taller-than peter michael))

; Rule: r_f48c94318fb5  |  Line: 6
; NL: "For every person, if that person does not jump when shooting, then Michael can block that person's shooting."
(assert (forall ((p Person))
  (=> (not (jumps-when-shooting p))
      (can-block-shooting michael p))))

; Rule: r_c9fffbe01dc1  |  Line: 7
; NL: "Michael cannot block the shooting of Windy."
(assert (not (can-block-shooting michael windy)))

; Rule: r_0223562f3008  |  Line: 8
; NL: "Every shooter who can jump when shooting is a great shooter."
(assert (forall ((p Person))
  (=> (and (is-shooter p) (jumps-when-shooting p))
      (is-great-shooter p))))

; Rule: r_44951c1a4dbe  |  Line: 9
; NL: "There exists a man m such that m is in Michael's class and Peter is shorter than m."
(assert (exists ((m Person))
  (and (is-man m)
       (is-in-michaels-class m)
       (is-shorter-than peter m))))

(assert (forall ((x Person) (y Person))
  (= (is-shorter-than x y) (is-taller-than y x))))