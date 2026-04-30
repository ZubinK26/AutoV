% query_liveness.lp — matches predicates in policy_model.lp
% No crash anywhere; some RM in working or prepared at 12 (not committed/aborted) — "stuck".

#show stuck_rm/2.
#show no_crashes/0.

no_crashes :-
    not has_any_crash.

has_any_crash :-
    resource_manager(RM),
    time(T),
    rm_crashed(RM, T).
has_any_crash :-
    transaction_manager(TM),
    time(T),
    tm_crashed(TM, T).

stuck_rm(RM, S) :-
    no_crashes,
    resource_manager(RM),
    rm_state(RM, S, 12),
    S != committed,
    S != aborted.

:- not has_stuck.
has_stuck :- stuck_rm(_, _).
