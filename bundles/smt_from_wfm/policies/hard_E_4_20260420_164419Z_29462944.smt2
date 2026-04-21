; ============================================================
; Bundle: hard_E_4_20260420_164419Z_29462944  |  Committed: 2026-04-20T17:13:26Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle hard_E_4_20260420_164419Z_29462944 ---
(declare-sort Vessel 0)
(declare-sort BerthSlot 0)
(declare-fun berth-slot-of (Vessel) BerthSlot)
(declare-fun is-premium (BerthSlot) Bool)
(declare-fun loa-of (Vessel) Int)
(declare-fun fits-morning-tide-gate (Vessel) Bool)
(declare-fun has-paid-priority-token (Vessel) Bool)
(declare-fun tonnage-fees-waived (Vessel) Bool)
(declare-fun manifest-submission-lead-time (Vessel) Int)
(declare-fun has-hazardous-class-1-cargo (Vessel) Bool)
(declare-fun declared-only-class-3-cargo (Vessel) Bool)
(declare-fun receives-lift-cap-increase (Vessel) Bool)
(declare-const mv-cornelia Vessel)

; Rule: r_6b0a1ecab1ff  |  Line: 0
; NL: "A berth slot is premium if and only if (the vessel’s declared length overall (LOA) is at most 240 meters and its arrival window fits entirely inside the morning tide gate) or the harbor master issues a paid priority token for that vessel."
(assert (forall ((v Vessel))
  (= (is-premium (berth-slot-of v))
     (or (and (<= (loa-of v) 240)
              (fits-morning-tide-gate v))
         (has-paid-priority-token v)))))

; Rule: r_8154757d452d  |  Line: 1
; NL: "MV Cornelia is a vessel that declared a length overall (LOA) of 235 meters."
(assert (= (loa-of mv-cornelia) 235))

; Rule: r_893620dde5b6  |  Line: 2
; NL: "MV Cornelia's arrival window fits entirely inside the morning tide gate."
(assert (fits-morning-tide-gate mv-cornelia))

; Rule: r_2bf6bb82ac9c  |  Line: 3
; NL: "MV Cornelia carries a paid priority token issued by the harbor master."
(assert (has-paid-priority-token mv-cornelia))

; Rule: r_078a263b495a  |  Line: 4
; NL: "Tonnage fees for a vessel are waived if and only if the vessel's berth slot is premium, the carrier submits manifests at least 48 hours ahead of the call, and no hazardous class-1 cargo is declared for that vessel."
(assert (forall ((v Vessel))
  (= (tonnage-fees-waived v)
     (and (is-premium (berth-slot-of v))
          (>= (manifest-submission-lead-time v) 48)
          (not (has-hazardous-class-1-cargo v))))))

; Rule: r_9a3a0cd533c5  |  Line: 5
; NL: "The carrier for MV Cornelia filed manifests 50 hours ahead of the call."
(assert (= (manifest-submission-lead-time mv-cornelia) 50))

; Rule: r_51f45d690807  |  Line: 6
; NL: "The carrier for MV Cornelia declared only class-3 cargo."
(assert (declared-only-class-3-cargo mv-cornelia))

; Rule: r_e2460d7de24d  |  Line: 7
; NL: "The declaration of only class-3 cargo implies no hazardous class-1 cargo was declared."
(assert (forall ((v Vessel))
  (=> (declared-only-class-3-cargo v)
      (not (has-hazardous-class-1-cargo v)))))

; Rule: r_292c2dec3499  |  Line: 8
; NL: "If tonnage fees for a vessel are waived, then the stevedore’s lift cap for that vessel's call increases by 20 percent."
(assert (forall ((v Vessel))
  (=> (tonnage-fees-waived v)
      (receives-lift-cap-increase v))))

; Rule: r_fe62014fe24c  |  Line: 9
; NL: "MV Cornelia receives a 20-percent lift cap increase for its current call."
(assert (receives-lift-cap-increase mv-cornelia))