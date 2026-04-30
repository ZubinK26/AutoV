% query_blocking.lp — matches predicates in policy_model.lp
% Blocking: prepared at 12, not crashed, no commit/abort received; TM has crashed at some time.

#show blocked_rm/1.
#show tm_crashed_at/1.
#show rm_state_trace/3.

blocked_rm(RM) :-
    resource_manager(RM),
    rm_state(RM, prepared, 12),
    -rm_crashed(RM, 12),
    not rm_received_commit(RM, 12),
    not rm_received_abort_decision(RM, 12).

tm_crashed_at(T) :-
    transaction_manager(TM),
    tm_crashed(TM, T),
    not tm_crashed(TM, T - 1),
    T > 0,
    time(T),
    time(T - 1).

rm_state_trace(RM, S, T) :-
    blocked_rm(RM),
    rm_state(RM, S, T),
    time(T).

% Require both: blocking pathology AND TM has crashed at least once
:- not has_blocking.
has_blocking :-
    blocked_rm(_),
    transaction_manager(TM),
    time(T),
    tm_crashed(TM, T).
