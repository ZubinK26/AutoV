% NL #84 — Scenario-pinned violation witness
% Pins: bx has two blinded instances at T=5 — inst1 duration 0 (expired), inst2 duration 3 (active).
% Expected (NL): blinded condition persists while any instance with Dur>0 remains.

time(5).
creature(bx).

holds(instance_duration(bx, blinded, inst1, 0), 5).
holds(instance_duration(bx, blinded, inst2, 3), 5).

viol :- holds(instance_duration(bx, blinded, inst2, 3), 5), not holds(condition(bx, blinded), 5).

:- not viol.
