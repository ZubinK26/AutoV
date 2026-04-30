% NL #55 — Scenario-pinned violation witness (Form 1)
% Pins: qc poisoned at time 5; qb is fixed attack target.

time(5).
creature(qc).
creature(qb).
holds(condition(qc, poisoned), 5).

viol :- holds(condition(qc, poisoned), 5), not has_disadvantage(attack_roll(qc, qb), 5).

:- not viol.
