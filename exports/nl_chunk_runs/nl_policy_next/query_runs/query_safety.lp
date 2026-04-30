% query_safety.lp — matches predicates in policy_model.lp (this folder)
% Disagreeing RMs (one committed, one aborted) at T=12, neither crashed.
% A correct 2PC encoding: expecting UNSAT for "bad" disagreement witness.

#show witness/3.

witness(rm1, rm2, 12) :-
    rm_state(rm1, committed, 12),
    rm_state(rm2, aborted, 12),
    -rm_crashed(rm1, 12),
    -rm_crashed(rm2, 12).

witness(rm1, rm3, 12) :-
    rm_state(rm1, committed, 12),
    rm_state(rm3, aborted, 12),
    -rm_crashed(rm1, 12),
    -rm_crashed(rm3, 12).

witness(rm2, rm3, 12) :-
    rm_state(rm2, committed, 12),
    rm_state(rm3, aborted, 12),
    -rm_crashed(rm2, 12),
    -rm_crashed(rm3, 12).

witness(rm2, rm1, 12) :-
    rm_state(rm1, committed, 12),
    rm_state(rm2, aborted, 12),
    -rm_crashed(rm1, 12),
    -rm_crashed(rm2, 12).

:- not has_witness.
has_witness :- witness(_, _, _).
