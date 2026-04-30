% NL #61 — Scenario-pinned violation witness (Form 1)
% Pins: qc restrained at time 5.

time(5).
creature(qc).
holds(condition(qc, restrained), 5).

viol :- holds(condition(qc, restrained), 5), holds(speed(qc, V), 5), V != 0.
viol :- holds(condition(qc, restrained), 5), not holds(speed(qc, 0), 5).

:- not viol.
