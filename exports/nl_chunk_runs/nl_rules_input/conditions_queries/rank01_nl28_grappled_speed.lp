% NL #28 — Scenario-pinned violation witness (Form 1)
% Pins: qc grappled by qg at time 5.

time(5).
creature(qc).
creature(qg).
holds(condition(qc, grappled(qg)), 5).

viol :- holds(condition(qc, grappled(qg)), 5), holds(speed(qc, V), 5), V != 0.
viol :- holds(condition(qc, grappled(qg)), 5), not holds(speed(qc, 0), 5).

:- not viol.
