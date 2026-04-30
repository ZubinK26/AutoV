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