; ============================================================
; Bundle: hard_PF_8_20260420_155230Z_bf9c42d7  |  Committed: 2026-04-20T17:10:44Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle hard_PF_8_20260420_155230Z_bf9c42d7 ---
(declare-sort Movie 0)
(declare-sort Person 0)
(declare-fun is-superhero-movie (Movie) Bool)
(declare-fun is-good-guy (Person) Bool)
(declare-fun is-bad-guy (Person) Bool)
(declare-fun wins (Person) Bool)
(declare-fun loses (Person) Bool)
(declare-fun fights (Person Person) Bool)
(declare-fun appears-in (Person Movie) Bool)
(declare-fun named-after (Movie Person) Bool)
(declare-const sir-digby Person)
(declare-const sir-digbys-nemesis Person)
(declare-const the-surprising-adventures-of-sir-digby-chicken-caesar Movie)

; Rule: r_a901b61b209d  |  Line: 0
; NL: "In every superhero movie, every good guy wins."
(assert (forall ((m Movie) (p Person))
  (=> (and (is-superhero-movie m) (is-good-guy p) (appears-in p m))
      (wins p))))

; Rule: r_7e88a808d50f  |  Line: 1
; NL: "The Surprising Adventures of Sir Digby Chicken Caesar is a superhero movie."
(assert (is-superhero-movie the-surprising-adventures-of-sir-digby-chicken-caesar))

; Rule: r_ab080b40082f  |  Line: 2
; NL: "Every good guy fights at least one bad guy."
(assert (forall ((p1 Person))
  (=> (is-good-guy p1)
      (exists ((p2 Person))
        (and (is-bad-guy p2) (fights p1 p2))))))

; Rule: r_4a5ba2b4123a  |  Line: 3
; NL: "Every bad guy fights at least one good guy."
(assert (forall ((p1 Person))
  (=> (is-bad-guy p1)
      (exists ((p2 Person))
        (and (is-good-guy p2) (fights p1 p2))))))

; Rule: r_2ba5d7cddc84  |  Line: 4
; NL: "Sir Digby fights Sir Digby's nemesis."
(assert (fights sir-digby sir-digbys-nemesis))

; Rule: r_479747f32ead  |  Line: 5
; NL: "If a superhero movie is named after a character, then that character is a good guy."
(assert (forall ((m Movie) (p Person))
  (=> (and (is-superhero-movie m) (named-after m p))
      (is-good-guy p))))

; Rule: r_49909b0c8779  |  Line: 6
; NL: "The movie The Surprising Adventures of Sir Digby Chicken Caesar is named after the character Sir Digby."
(assert (named-after the-surprising-adventures-of-sir-digby-chicken-caesar sir-digby))

; Rule: r_7e4a24b063ba  |  Line: 7
; NL: "If a person wins a fight, then the person whom they are fighting loses that fight."
(assert (forall ((p1 Person) (p2 Person))
  (=> (and (fights p1 p2) (wins p1))
      (loses p2))))

; Rule: r_5ff67f391490  |  Line: 8
; NL: "If a superhero movie is named after a character, then that character appears in that movie."
(assert (forall ((m Movie) (p Person))
  (=> (and (is-superhero-movie m) (named-after m p))
      (appears-in p m))))

; Rule: r_39326156259c  |  Line: 9
; NL: "Sir Digby’s nemesis loses."
(assert (loses sir-digbys-nemesis))