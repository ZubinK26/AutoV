% Bundle: nlchunk_20260426_170115Z_d6c1e903
% Rule: r_f2b978efcef5  |  line_index: 0  |  NL: There are exactly three resource managers.
:- not { resource_manager(X) } = 3.
% Rule: r_f7d50991c75f  |  line_index: 1  |  NL: rm1 is a resource manager.
resource_manager(rm1).
% Rule: r_ced610c0d74d  |  line_index: 2  |  NL: rm2 is a resource manager.
resource_manager(rm2).
% Rule: r_56e2875d78a5  |  line_index: 3  |  NL: rm3 is a resource manager.
resource_manager(rm3).
% Rule: r_ee06d65e3a8a  |  line_index: 4  |  NL: There is exactly one transaction manager.
:- not { transaction_manager(X) } = 1.
% Rule: r_22acefd14205  |  line_index: 5  |  NL: tm is a transaction manager.
transaction_manager(tm).
% Rule: r_728b707ee5d1  |  line_index: 6  |  NL: Time proceeds in discrete steps numbered 0 through 12.
time(0..12).
% Rule: r_985aebe41bfe  |  line_index: 7  |  NL: At time step 0, every resource manager is in the working state.
holds(state(RM, working), 0) :- resource_manager(RM).
% Rule: r_8de94bb119d6  |  line_index: 8  |  NL: At time step 0, the transaction manager is in the init state.
holds(state(TM, init), 0) :- transaction_manager(TM).
% Rule: r_b38fa6d7f7d0  |  line_index: 9  |  NL: At time step 0, no resource manager has crashed.
-holds(crashed(RM), 0) :- resource_manager(RM).
% Rule: r_295a96a96139  |  line_index: 10  |  NL: At time step 0, the transaction manager has not crashed.
-holds(crashed(TM), 0) :- transaction_manager(TM).
% Rule: r_6a7031fddeb6  |  line_index: 11  |  NL: Every resource manager is in exactly one state at each time step.
1 { holds(state(RM, S), T) : rm_state(S) } 1 :- resource_manager(RM), time(T).
% Rule: r_cab82a91f31d  |  line_index: 12  |  NL: The possible states for a resource manager are working, prepared, committed, and aborted.
rm_state(working).
rm_state(prepared).
rm_state(committed).
rm_state(aborted).
% Rule: r_addef38bbe3e  |  line_index: 13  |  NL: The transaction manager is in exactly one state at each time step.
1 { holds(state(TM, S), T) : tm_state(S) } 1 :- transaction_manager(TM), time(T).
tm_state(init).
tm_state(S) :- rm_state(S).

% Bundle: nlchunk_20260426_174107Z_c4d7c26f
% Rule: r_f2b978efcef5  |  line_index: 0  |  NL: There are exactly three resource managers.
:- not { resource_manager(X) } = 3.
% Rule: r_f7d50991c75f  |  line_index: 1  |  NL: rm1 is a resource manager.
resource_manager(rm1).
% Rule: r_ced610c0d74d  |  line_index: 2  |  NL: rm2 is a resource manager.
resource_manager(rm2).
% Rule: r_56e2875d78a5  |  line_index: 3  |  NL: rm3 is a resource manager.
resource_manager(rm3).
% Rule: r_ee06d65e3a8a  |  line_index: 4  |  NL: There is exactly one transaction manager.
:- not { transaction_manager(X) } = 1.
% Rule: r_22acefd14205  |  line_index: 5  |  NL: tm is a transaction manager.
transaction_manager(tm).
% Rule: r_728b707ee5d1  |  line_index: 6  |  NL: Time proceeds in discrete steps numbered 0 through 12.
time(0..12).
% Rule: r_985aebe41bfe  |  line_index: 7  |  NL: At time step 0, every resource manager is in the working state.
holds(state(RM, working), 0) :- resource_manager(RM).
% Rule: r_8de94bb119d6  |  line_index: 8  |  NL: At time step 0, the transaction manager is in the init state.
holds(state(TM, init), 0) :- transaction_manager(TM).
% Rule: r_b38fa6d7f7d0  |  line_index: 9  |  NL: At time step 0, no resource manager has crashed.
-holds(crashed(RM), 0) :- resource_manager(RM).
% Rule: r_295a96a96139  |  line_index: 10  |  NL: At time step 0, the transaction manager has not crashed.
-holds(crashed(TM), 0) :- transaction_manager(TM).
% Rule: r_6a7031fddeb6  |  line_index: 11  |  NL: Every resource manager is in exactly one state at each time step.
1 { holds(state(RM, S), T) : rm_state(S) } 1 :- resource_manager(RM), time(T).
% Rule: r_cab82a91f31d  |  line_index: 12  |  NL: The possible states for a resource manager are working, prepared, committed, and aborted.
rm_state(working).
rm_state(prepared).
rm_state(committed).
rm_state(aborted).
% Rule: r_addef38bbe3e  |  line_index: 13  |  NL: The transaction manager is in exactly one state at each time step.
1 { holds(state(TM, S), T) : tm_state(S) } 1 :- transaction_manager(TM), time(T).
% Rule: r_93b00032bd9e  |  line_index: 0  |  NL: The state of the transaction manager must be exactly one of the following: init, collecting, committed, or aborted.
tm_state(init).
tm_state(collecting).
tm_state(committed).
tm_state(aborted).
% Rule: r_a822b14806a3  |  line_index: 1  |  NL: If a resource manager is in the working state at time T, then that resource manager is permitted to transition to the prepared state at time T plus 1.
permitted_transition(RM, working, prepared, T) :- resource_manager(RM), holds(state(RM, working), T), time(T).
% Rule: r_a02de42412b2  |  line_index: 2  |  NL: If a resource manager is in the working state at time T, then that resource manager is permitted to transition to the aborted state at time T plus 1.
permitted_transition(RM, working, aborted, T) :- resource_manager(RM), holds(state(RM, working), T), time(T).
% Rule: r_6c2ee83d8b79  |  line_index: 3  |  NL: If a resource manager transitions to the prepared state at time T plus 1, then at least one prepared message from that resource manager is sent at time T plus 1.
sent(RM, prepared_msg, T+1) :- resource_manager(RM), holds(state(RM, prepared), T+1), not holds(state(RM, prepared), T), time(T), time(T+1).
% Rule: r_bd25c07f5dbd  |  line_index: 4  |  NL: If a resource manager transitions to the aborted state at time T plus 1 from the working state, then at least one abort message from that resource manager is sent at time T plus 1.
sent(RM, abort_msg, T+1) :- resource_manager(RM), holds(state(RM, working), T), holds(state(RM, aborted), T+1), time(T), time(T+1).
% Rule: r_08533c0f4487  |  line_index: 5  |  NL: If the transaction manager is in the init state at time T and the transaction manager has not crashed at time T, then the transaction manager transitions to the collecting state at time T plus 1.
holds(state(TM, collecting), T+1) :- transaction_manager(TM), holds(state(TM, init), T), -holds(crashed(TM), T), time(T), time(T+1).
% Rule: r_67cc304e5946  |  line_index: 6  |  NL: The transaction manager is considered to have received a prepared vote from a specific resource manager at time T if at least one prepared message from that resource manager was sent at any time less than or equal to T.
received_vote(TM, RM, prepared, T) :- transaction_manager(TM), resource_manager(RM), sent(RM, prepared_msg, T1), T1 <= T, time(T), time(T1).
% Rule: r_54ca7b21295a  |  line_index: 7  |  NL: The transaction manager is considered to have received an abort vote from a specific resource manager at time T if at least one abort message from that resource manager was sent at any time less than or equal to T.
received_vote(TM, RM, abort, T) :- transaction_manager(TM), resource_manager(RM), sent(RM, abort_msg, T1), T1 <= T, time(T), time(T1).
% Rule: r_3c15924adb5f  |  line_index: 8  |  NL: If the transaction manager is in the collecting state at time T, the transaction manager has received a prepared vote from resource manager rm1 at time T, the transaction manager has received a prepared vote from resource manager rm2 at time T, the transaction manager has received a prepared vote from resource manager rm3 at time T, and the transaction manager has not crashed at time T, then the transaction manager transitions to the committed state at time T plus 1.
holds(state(TM, committed), T+1) :- transaction_manager(TM), holds(state(TM, collecting), T), received_vote(TM, rm1, prepared, T), received_vote(TM, rm2, prepared, T), received_vote(TM, rm3, prepared, T), -holds(crashed(TM), T), time(T), time(T+1).
% Rule: r_4566c0994fba  |  line_index: 9  |  NL: If the transaction manager is in the collecting state at time T, the transaction manager has received an abort vote from at least one resource manager at time T, and the transaction manager has not crashed at time T, then the transaction manager transitions to the aborted state at time T plus 1.
holds(state(TM, aborted), T+1) :- transaction_manager(TM), holds(state(TM, collecting), T), received_vote(TM, RM, abort, T), resource_manager(RM), -holds(crashed(TM), T), time(T), time(T+1).