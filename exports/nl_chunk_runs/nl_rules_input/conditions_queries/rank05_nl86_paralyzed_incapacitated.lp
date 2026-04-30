% NL #86 — Scenario-pinned violation witness
% Pins: px paralyzed at T=5.
% Expected (NL): px also has all incapacitated effects → holds(condition(_, incapacitated), _).

time(5).
creature(px).

holds(condition(px, paralyzed), 5).

viol :- holds(condition(px, paralyzed), 5), not holds(condition(px, incapacitated), 5).

:- not viol.
