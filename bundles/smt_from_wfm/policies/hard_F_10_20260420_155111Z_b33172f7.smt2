; ============================================================
; Bundle: hard_F_10_20260420_155111Z_b33172f7  |  Committed: 2026-04-20T17:09:57Z
; ============================================================
(set-logic ALL)

; --- New declarations for bundle hard_F_10_20260420_155111Z_b33172f7 ---
(declare-sort MusicPiece 0)
(declare-sort Person 0)
(declare-sort Orchestra 0)
(declare-const symphony-no-9 MusicPiece)
(declare-const beethoven Person)
(declare-const vienna-music-society Orchestra)
(declare-fun is-music-piece (MusicPiece) Bool)
(declare-fun writes (Person MusicPiece) Bool)
(declare-fun is-composer (Person) Bool)
(declare-fun premiered (Orchestra MusicPiece) Bool)
(declare-fun leads (Person Orchestra) Bool)
(declare-fun is-conductor (Person) Bool)

; Rule: r_ed05c0ff4b35  |  Line: 0
; NL: "Symphony No. 9 is a music piece."
(assert (is-music-piece symphony-no-9))

; Rule: r_a0fe09b4bee3  |  Line: 1
; NL: "For every person: if the person writes a music piece, then the person is a composer."
(assert (forall ((p Person))
  (=> (exists ((m MusicPiece)) (writes p m))
      (is-composer p))))

; Rule: r_8bf852c2d6b7  |  Line: 2
; NL: "Beethoven wrote Symphony No. 9."
(assert (writes beethoven symphony-no-9))

; Rule: r_514e4cd07c29  |  Line: 3
; NL: "The Vienna Music Society premiered Symphony No. 9."
(assert (premiered vienna-music-society symphony-no-9))

; Rule: r_de6398c62d15  |  Line: 4
; NL: "The Vienna Music Society is an orchestra."
; This is captured by the sort declaration and the constant's type.
(assert true)

; Rule: r_806c9e3c713f  |  Line: 5
; NL: "Beethoven leads the Vienna Music Society."
(assert (leads beethoven vienna-music-society))

; Rule: r_50b67574baeb  |  Line: 6
; NL: "For every orchestra, there exists exactly one conductor who leads that orchestra."
(assert (forall ((o Orchestra))
  (exists ((c Person))
    (and (is-conductor c)
         (leads c o)
         (forall ((other Person))
           (=> (and (is-conductor other) (leads other o))
               (= c other)))))))

; Rule: r_34d347fa04aa  |  Line: 7
; NL: "Beethoven is a composer."
(assert (is-composer beethoven))