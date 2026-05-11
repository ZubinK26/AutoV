; ============================================================
; Bundle: demo_20260419_180311Z_09df60e0  |  Committed: 2026-04-19T22:48:06Z
; ============================================================
(set-logic ALL)
; --- New declarations for bundle demo_20260419_180311Z_09df60e0 ---
(declare-sort Building 0)
(declare-sort Apartment 0)
(declare-sort Animal 0)
(declare-sort Person 0)

(declare-fun is-managed-building (Building) Bool)
(declare-fun pets-allowed (Building) Bool)
(declare-fun is-pet (Animal) Bool)
(declare-fun is-cat (Animal) Bool)
(declare-fun owns (Person Animal) Bool)
(declare-fun apartment-in (Apartment Building) Bool)
(declare-fun security-deposit (Apartment) Int)
(declare-fun monthly-rent (Apartment) Int)
(declare-fun will-rent (Person Apartment) Bool)
(declare-fun allowed-to-move-in-with (Person Apartment Animal) Bool)

(declare-const fluffy Animal)
(declare-const tom Person)
(declare-const the-olive-garden Building)

; Rule: r_5d9e0574fa6d  |  Line: 0
; NL: "Pets are allowed in at least one managed building."
(assert (exists ((b Building))
  (and (is-managed-building b) (pets-allowed b))))

; Rule: r_eb0d8dbff223  |  Line: 1
; NL: "A security deposit is required to rent an apartment in any managed building."
(assert (forall ((a Apartment) (b Building))
  (=> (and (apartment-in a b) (is-managed-building b))
      (> (security-deposit a) 0))))

; Rule: r_e51d5d2e803c  |  Line: 2
; NL: "The security deposit for an apartment is greater than or equal to one month's rent for that apartment."
(assert (forall ((a Apartment))
  (>= (security-deposit a) (monthly-rent a))))

; Rule: r_94ec0c8ba800  |  Line: 3
; NL: "Fluffy is a cat."
(assert (is-cat fluffy))

; Rule: r_4f131729e2ce  |  Line: 4
; NL: "Tom owns Fluffy."
(assert (owns tom fluffy))

; Rule: r_e4515a16a1f2  |  Line: 5
; NL: "Every cat is a pet."
(assert (forall ((a Animal))
  (=> (is-cat a) (is-pet a))))

; Rule: r_bc4f98ba371c  |  Line: 6
; NL: "The Olive Garden is a managed building."
(assert (is-managed-building the-olive-garden))

; Rule: r_e58dfdd8843a  |  Line: 7
; NL: "The monthly rent for an apartment at The Olive Garden is $2000."
(assert (forall ((a Apartment))
  (=> (apartment-in a the-olive-garden)
      (= (monthly-rent a) 2000))))

; Rule: r_4820643c70da  |  Line: 8
; NL: "Tom will rent an apartment in a managed building if and only if Tom is allowed to move into that apartment with Fluffy, and the security deposit for that apartment is less than or equal to $1500."
(assert (forall ((a Apartment) (b Building))
  (=> (and (apartment-in a b) (is-managed-building b))
      (= (will-rent tom a)
         (and (allowed-to-move-in-with tom a fluffy)
              (<= (security-deposit a) 1500))))))

; Rule: r_89f095449a53  |  Line: 9
; NL: "$2000 is greater than $1500."
(assert (> 2000 1500))

; Rule: r_0652fade7f68  |  Line: 10
; NL: "In conclusion: Tom will rent an apartment in The Olive Garden."
(assert (exists ((a Apartment))
  (and (apartment-in a the-olive-garden)
       (will-rent tom a))))