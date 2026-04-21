; ============================================================
; Bundle: hard_R_5_20260420_155956Z_b96b26eb  |  Committed: 2026-04-20T17:12:47Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle hard_R_5_20260420_155956Z_b96b26eb ---
(declare-sort Criterion 0)
(declare-sort Vendor 0)
(declare-sort Subsidiary 0)
(declare-fun is-adopted-by-board (Criterion) Bool)
(declare-fun satisfies-criterion (Vendor Criterion) Bool)
(declare-fun is-subsidiary-of (Subsidiary Vendor) Bool)
(declare-fun on-sanctions-watchlist (Subsidiary) Bool)
(declare-fun qualifies-for-restricted-path (Vendor) Bool)
(declare-fun is-published-in-april-addendum (Criterion) Bool)
(declare-const nimbus-cloud Vendor)
(declare-fun is-sanction-sensitive (Vendor) Bool)
(declare-fun offer-is-void (Vendor) Bool)

; Rule: r_d3db4a4b573a  |  Line: 0
; NL: "For every criterion in the set of criteria adopted by the procurement compliance board: if a vendor satisfies that criterion under the board’s published stress-test scenarios and no subsidiary of that vendor is on the sanctions watchlist during the review window, then that vendor qualifies for the restricted federal data path."
(assert (forall ((v Vendor))
  (=> (and (forall ((c Criterion))
             (=> (is-adopted-by-board c)
                 (satisfies-criterion v c)))
           (not (exists ((s Subsidiary))
                  (and (is-subsidiary-of s v)
                       (on-sanctions-watchlist s)))))
      (qualifies-for-restricted-path v))))

; Rule: r_30168bdea460  |  Line: 1
; NL: "Nimbus Cloud satisfies every criterion that the board published in the April addendum."
(assert (forall ((c Criterion))
  (=> (is-published-in-april-addendum c)
      (satisfies-criterion nimbus-cloud c))))

; Rule: r_332e246b56ae  |  Line: 2
; NL: "No subsidiary of Nimbus Cloud appeared on the sanctions watchlist during the review window."
(assert (not (exists ((s Subsidiary))
  (and (is-subsidiary-of s nimbus-cloud)
       (on-sanctions-watchlist s)))))

; Rule: r_6fd7c1cdbf4a  |  Line: 4
; NL: "If Nimbus Cloud is sanction-sensitive, then the offer for the restricted federal data path to Nimbus Cloud is void."
(assert (=> (is-sanction-sensitive nimbus-cloud)
            (offer-is-void nimbus-cloud)))

; Rule: r_058768ef0a67  |  Line: 5
; NL: "Nimbus Cloud qualifies for the restricted federal data path."
(assert (qualifies-for-restricted-path nimbus-cloud))

; Rule: r_153cdd0a249a  |  Line: 6
; NL: "The offer for the restricted federal data path to Nimbus Cloud is not void."
(assert (not (offer-is-void nimbus-cloud)))