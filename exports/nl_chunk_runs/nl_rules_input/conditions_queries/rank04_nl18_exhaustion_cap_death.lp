% NL #18 — Scenario-pinned violation witness
% Pins: cx at exhaustion 5 at T=0; impose +2 at T=0; times 0..1.
% Expected (NL): level capped at 6 and creature dies at T=1.
% Note: impose rule uses L2=L1+V, L2<=6 — 5+2>6 so the impose head does not apply; a separate choice rule picks a level each tick,
% so arbitrary L at T=1 can accidentally satisfy level 6 without semantics matching “cap then die.”

time(0).
time(1).
creature(cx).

holds(exhaustion_level(cx, 5), 0).
occurs(impose_exhaustion(cx, 2), 0).

viol :- holds(exhaustion_level(cx, 5), 0), occurs(impose_exhaustion(cx, 2), 0), time(1), not holds(exhaustion_level(cx, 6), 1).
viol :- holds(exhaustion_level(cx, 5), 0), occurs(impose_exhaustion(cx, 2), 0), time(1), not occurs(die(cx), 1).

:- not viol.
