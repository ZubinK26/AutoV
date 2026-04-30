% NL #20 — Scenario-pinned violation witness
% Pins: rx at exhaustion 1 at T=0; remove 2 at T=0; times 0..1.
% Expected (NL): level set to 0 (not negative). Policy: remove rule when L2=L1-V and L2>=0,
% plus “falls below” rule holds(exhaustion_level(C,0),T+1) :- ..., L1-V < 0.
% Symmetric structural worry to NL#18: choice rule also fixes exhaustion each tick.

time(0).
time(1).
creature(rx).

holds(exhaustion_level(rx, 1), 0).
occurs(remove_exhaustion(rx, 2), 0).

viol :- holds(exhaustion_level(rx, 1), 0), occurs(remove_exhaustion(rx, 2), 0), time(1), not holds(exhaustion_level(rx, 0), 1).

:- not viol.
