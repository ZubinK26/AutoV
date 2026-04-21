; ============================================================
; Bundle: hard_PF_9_20260420_155252Z_802696c5  |  Committed: 2026-04-20T17:11:22Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle hard_PF_9_20260420_155252Z_802696c5 ---
(declare-sort Building 0)
(declare-sort Person 0)
(declare-sort Apartment 0)
(declare-sort Pet 0)
(declare-fun is-managed (Building) Bool)
(declare-fun allows-pets (Building) Bool)
(declare-fun rents-apartment (Person Apartment) Bool)
(declare-fun building-of (Apartment) Building)
(declare-fun pays-security-deposit (Person Apartment) Bool)
(declare-fun security-deposit-amount (Apartment) Int)
(declare-fun monthly-rent (Apartment) Int)
(declare-const fluffy Pet)
(declare-const tom Person)
(declare-fun is-cat (Pet) Bool)
(declare-fun is-pet (Pet) Bool)
(declare-fun owns-pet (Person Pet) Bool)
(declare-const olive-garden Building)
(declare-fun allowed-to-move-in-with (Person Apartment Pet) Bool)

; Rule: r_2b7ecb094d70  |  Line: 0
; NL: "There exists a managed building such that the managed building allows pets."
(assert (exists ((b Building)) (and (is-managed b) (allows-pets b))))

; Rule: r_f5d7ed840fd4  |  Line: 1
; NL: "Every person who rents an apartment in a managed building is required to pay a security deposit."
(assert (forall ((p Person) (a Apartment))
  (=> (and (rents-apartment p a) (is-managed (building-of a)))
      (pays-security-deposit p a))))

; Rule: r_05ae9844e625  |  Line: 2
; NL: "The security deposit for an apartment is greater than or equal to one month's rent for that apartment."
(assert (forall ((a Apartment))
  (>= (security-deposit-amount a) (monthly-rent a))))

; Rule: r_8743b5bc7010  |  Line: 3
; NL: "Fluffy is a cat."
(assert (is-cat fluffy))

; Rule: r_a985e4e609a1  |  Line: 4
; NL: "Fluffy is owned by Tom."
(assert (owns-pet tom fluffy))

; Rule: r_8811b0af6acd  |  Line: 5
; NL: "Every cat is a pet."
(assert (forall ((p Pet)) (=> (is-cat p) (is-pet p))))

; Rule: r_51bb89c70964  |  Line: 6
; NL: "The Olive Garden is a managed building."
(assert (is-managed olive-garden))

; Rule: r_a904f2e3069e  |  Line: 7
; NL: "The monthly rent for every apartment at the Olive Garden is $2000."
(assert (forall ((a Apartment))
  (=> (= (building-of a) olive-garden) (= (monthly-rent a) 2000))))

; Rule: r_b401fe36602f  |  Line: 8
; NL: "If Tom rents an apartment in a managed building, then Tom is allowed to move into that apartment with Fluffy."
(assert (forall ((a Apartment))
  (=> (and (rents-apartment tom a) (is-managed (building-of a)))
      (allowed-to-move-in-with tom a fluffy))))

; Rule: r_bd58be5404c1  |  Line: 9
; NL: "If Tom rents an apartment in a managed building, then the security deposit for that apartment is less than or equal to $1500."
(assert (forall ((a Apartment))
  (=> (and (rents-apartment tom a) (is-managed (building-of a)))
      (<= (security-deposit-amount a) 1500))))

; Rule: r_2938b7cec92d  |  Line: 10
; NL: "If Tom is allowed to move into that apartment with Fluffy and the security deposit for that apartment is less than or equal to $1500, then Tom will rent an apartment in a managed building."
(assert (forall ((a Apartment))
  (=> (and (allowed-to-move-in-with tom a fluffy) (<= (security-deposit-amount a) 1500))
      (exists ((a2 Apartment)) (and (rents-apartment tom a2) (is-managed (building-of a2)))))))

; Rule: r_9c32a49f12d3  |  Line: 11
; NL: "$2000 is greater than $1500."
(assert (> 2000 1500))

; Rule: r_9f6de8783a93  |  Line: 12
; NL: "Tom will rent an apartment in the Olive Garden."
(assert (exists ((a Apartment)) (and (rents-apartment tom a) (= (building-of a) olive-garden))))