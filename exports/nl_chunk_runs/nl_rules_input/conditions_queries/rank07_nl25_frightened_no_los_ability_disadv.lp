% NL #25 — Scenario-pinned violation witness
% Pins: qc frightened of src at T=5; qc not in LOS of src (open-world: no holds(in_line_of_sight));
% exhaustion 0 and not poisoned so frightened LOS rule is the only ability-check disadvantage source.
% Expected (NL / rules): frightened does not grant ability-check disadvantage without LOS.

time(5).
creature(qc).
creature(src).

ability_check_type(ac_nl25).

holds(condition(qc, frightened(src)), 5).
holds(exhaustion_level(qc, 0), 5).

% Isolate frightened-vs-LOS: forbid other modeled sources of ability-check disadvantage.
:- holds(exhaustion_level(qc, L), 5), L != 0.
:- holds(condition(qc, poisoned), 5).

viol :- holds(condition(qc, frightened(src)), 5), holds(exhaustion_level(qc, 0), 5), not holds(in_line_of_sight(qc, src), 5), ability_check_type(ac_nl25), has_disadvantage(ability_check(qc, ac_nl25), 5).

:- not viol.
