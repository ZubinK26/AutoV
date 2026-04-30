% Bundle: nlchunk_20260426_182457Z_df73e1fa
% Rule: r_b2d6b0b20056  |  line_index: 0  |  NL: There are exactly three resource managers.
:- not { resource_manager(RM) } = 3.
% Rule: r_81504e78700a  |  line_index: 1  |  NL: rm1 is a resource manager.
resource_manager(rm1).
% Rule: r_904b8f810556  |  line_index: 2  |  NL: rm2 is a resource manager.
resource_manager(rm2).
% Rule: r_0cb1ca807137  |  line_index: 3  |  NL: rm3 is a resource manager.
resource_manager(rm3).
% Rule: r_9a7062a802a8  |  line_index: 4  |  NL: There is exactly one transaction manager.
:- not { transaction_manager(TM) } = 1.
% Rule: r_d6562ce342b6  |  line_index: 5  |  NL: tm is a transaction manager.
transaction_manager(tm).
% Rule: r_ac748d4ff3c6  |  line_index: 6  |  NL: Time proceeds in discrete steps numbered 0 through 12.
time(0..12).
% Rule: r_9ea13ebeec66  |  line_index: 7  |  NL: Every resource manager is in exactly one state at any given time step.
1 { rm_state(RM, S, T) : state_type_rm(S) } 1 :- resource_manager(RM), time(T).
% Rule: r_c31408db0c86  |  line_index: 8  |  NL: Every resource manager state must be one of: working, prepared, committed, or aborted.
state_type_rm(working).
state_type_rm(prepared).
state_type_rm(committed).
state_type_rm(aborted).
% Rule: r_d1abe654a7dc  |  line_index: 9  |  NL: The transaction manager is in exactly one state at any given time step.
1 { tm_state(TM, S, T) : state_type_tm(S) } 1 :- transaction_manager(TM), time(T).
% Rule: r_cebb85dcaff5  |  line_index: 10  |  NL: The transaction manager state must be one of: init, collecting, committed, or aborted.
state_type_tm(init).
state_type_tm(collecting).
state_type_tm(committed).
state_type_tm(aborted).
% Rule: r_bc081d52621f  |  line_index: 11  |  NL: At time step 0, every resource manager is in the working state.
rm_state(RM, working, 0) :- resource_manager(RM).

% Bundle: nlchunk_20260426_182611Z_7764180c
% Rule: r_b2d6b0b20056  |  line_index: 0  |  NL: There are exactly three resource managers.
:- not { resource_manager(RM) } = 3.
% Rule: r_81504e78700a  |  line_index: 1  |  NL: rm1 is a resource manager.
resource_manager(rm1).
% Rule: r_904b8f810556  |  line_index: 2  |  NL: rm2 is a resource manager.
resource_manager(rm2).
% Rule: r_0cb1ca807137  |  line_index: 3  |  NL: rm3 is a resource manager.
resource_manager(rm3).
% Rule: r_9a7062a802a8  |  line_index: 4  |  NL: There is exactly one transaction manager.
:- not { transaction_manager(TM) } = 1.
% Rule: r_d6562ce342b6  |  line_index: 5  |  NL: tm is a transaction manager.
transaction_manager(tm).
% Rule: r_ac748d4ff3c6  |  line_index: 6  |  NL: Time proceeds in discrete steps numbered 0 through 12.
time(0..12).
% Rule: r_9ea13ebeec66  |  line_index: 7  |  NL: Every resource manager is in exactly one state at any given time step.
1 { rm_state(RM, S, T) : state_type_rm(S) } 1 :- resource_manager(RM), time(T).
% Rule: r_c31408db0c86  |  line_index: 8  |  NL: Every resource manager state must be one of: working, prepared, committed, or aborted.
state_type_rm(working).
state_type_rm(prepared).
state_type_rm(committed).
state_type_rm(aborted).
% Rule: r_d1abe654a7dc  |  line_index: 9  |  NL: The transaction manager is in exactly one state at any given time step.
1 { tm_state(TM, S, T) : state_type_tm(S) } 1 :- transaction_manager(TM), time(T).
% Rule: r_cebb85dcaff5  |  line_index: 10  |  NL: The transaction manager state must be one of: init, collecting, committed, or aborted.
state_type_tm(init).
state_type_tm(collecting).
state_type_tm(committed).
state_type_tm(aborted).
% Rule: r_bc081d52621f  |  line_index: 11  |  NL: At time step 0, every resource manager is in the working state.
rm_state(RM, working, 0) :- resource_manager(RM).
% Rule: r_136e744c5e1d  |  line_index: 0  |  NL: At time step 0, the transaction manager is in the init state.
tm_state(TM, init, 0) :- transaction_manager(TM).
% Rule: r_5ac9bf2e41c3  |  line_index: 1  |  NL: At time step 0, every resource manager has not crashed.
-rm_crashed(RM, 0) :- resource_manager(RM).
% Rule: r_173546f119c6  |  line_index: 2  |  NL: At time step 0, the transaction manager has not crashed.
-tm_crashed(TM, 0) :- transaction_manager(TM).
% Rule: r_81823e114654  |  line_index: 3  |  NL: Every resource manager either has crashed at a given time step or has not crashed at that time step.
1 { rm_crashed(RM, T); -rm_crashed(RM, T) } 1 :- resource_manager(RM), time(T).
% Rule: r_cabba388a083  |  line_index: 4  |  NL: The transaction manager either has crashed at a given time step or has not crashed at that time step.
1 { tm_crashed(TM, T); -tm_crashed(TM, T) } 1 :- transaction_manager(TM), time(T).
% Rule: r_78fd1ed2f124  |  line_index: 5  |  NL: If a resource manager has crashed at time step T, then that resource manager has crashed at time step T + 1.
rm_crashed(RM, T + 1) :- rm_crashed(RM, T), time(T), time(T + 1).
% Rule: r_22e408788ea7  |  line_index: 6  |  NL: If the transaction manager has crashed at time step T, then the transaction manager has crashed at time step T + 1.
tm_crashed(TM, T + 1) :- tm_crashed(TM, T), time(T), time(T + 1).
% Rule: r_5e917500a5e4  |  line_index: 7  |  NL: If a resource manager is in the working state at time step T and has not crashed at time step T, then exactly one of the following holds at time step T + 1: the resource manager is in the working state, the resource manager is in the prepared state, or the resource manager is in the aborted state.
1 { rm_state(RM, working, T + 1); rm_state(RM, prepared, T + 1); rm_state(RM, aborted, T + 1) } 1 :- rm_state(RM, working, T), -rm_crashed(RM, T), time(T), time(T + 1).
% Rule: r_03c1d93eeca5  |  line_index: 8  |  NL: If a resource manager is in the working state at time step T and is in the prepared state at time step T + 1, then exactly one prepared message from that resource manager is sent at time step T + 1.
1 { sent_prepared(RM, T + 1) } 1 :- rm_state(RM, working, T), rm_state(RM, prepared, T + 1), time(T), time(T + 1).
% Rule: r_37f3f5a041c3  |  line_index: 9  |  NL: If a resource manager is in the working state at time step T and is in the aborted state at time step T + 1, then exactly one abort vote message from that resource manager is sent at time step T + 1.
1 { sent_abort_vote(RM, T + 1) } 1 :- rm_state(RM, working, T), rm_state(RM, aborted, T + 1), time(T), time(T + 1).

% Bundle: nlchunk_20260426_182723Z_9ae2aba5
% Rule: r_b2d6b0b20056  |  line_index: 0  |  NL: There are exactly three resource managers.
:- not { resource_manager(RM) } = 3.
% Rule: r_81504e78700a  |  line_index: 1  |  NL: rm1 is a resource manager.
resource_manager(rm1).
% Rule: r_904b8f810556  |  line_index: 2  |  NL: rm2 is a resource manager.
resource_manager(rm2).
% Rule: r_0cb1ca807137  |  line_index: 3  |  NL: rm3 is a resource manager.
resource_manager(rm3).
% Rule: r_9a7062a802a8  |  line_index: 4  |  NL: There is exactly one transaction manager.
:- not { transaction_manager(TM) } = 1.
% Rule: r_d6562ce342b6  |  line_index: 5  |  NL: tm is a transaction manager.
transaction_manager(tm).
% Rule: r_ac748d4ff3c6  |  line_index: 6  |  NL: Time proceeds in discrete steps numbered 0 through 12.
time(0..12).
% Rule: r_9ea13ebeec66  |  line_index: 7  |  NL: Every resource manager is in exactly one state at any given time step.
1 { rm_state(RM, S, T) : state_type_rm(S) } 1 :- resource_manager(RM), time(T).
% Rule: r_c31408db0c86  |  line_index: 8  |  NL: Every resource manager state must be one of: working, prepared, committed, or aborted.
state_type_rm(working).
state_type_rm(prepared).
state_type_rm(committed).
state_type_rm(aborted).
% Rule: r_d1abe654a7dc  |  line_index: 9  |  NL: The transaction manager is in exactly one state at any given time step.
1 { tm_state(TM, S, T) : state_type_tm(S) } 1 :- transaction_manager(TM), time(T).
% Rule: r_cebb85dcaff5  |  line_index: 10  |  NL: The transaction manager state must be one of: init, collecting, committed, or aborted.
state_type_tm(init).
state_type_tm(collecting).
state_type_tm(committed).
state_type_tm(aborted).
% Rule: r_bc081d52621f  |  line_index: 11  |  NL: At time step 0, every resource manager is in the working state.
rm_state(RM, working, 0) :- resource_manager(RM).
% Rule: r_136e744c5e1d  |  line_index: 0  |  NL: At time step 0, the transaction manager is in the init state.
tm_state(TM, init, 0) :- transaction_manager(TM).
% Rule: r_5ac9bf2e41c3  |  line_index: 1  |  NL: At time step 0, every resource manager has not crashed.
-rm_crashed(RM, 0) :- resource_manager(RM).
% Rule: r_173546f119c6  |  line_index: 2  |  NL: At time step 0, the transaction manager has not crashed.
-tm_crashed(TM, 0) :- transaction_manager(TM).
% Rule: r_81823e114654  |  line_index: 3  |  NL: Every resource manager either has crashed at a given time step or has not crashed at that time step.
1 { rm_crashed(RM, T); -rm_crashed(RM, T) } 1 :- resource_manager(RM), time(T).
% Rule: r_cabba388a083  |  line_index: 4  |  NL: The transaction manager either has crashed at a given time step or has not crashed at that time step.
1 { tm_crashed(TM, T); -tm_crashed(TM, T) } 1 :- transaction_manager(TM), time(T).
% Rule: r_78fd1ed2f124  |  line_index: 5  |  NL: If a resource manager has crashed at time step T, then that resource manager has crashed at time step T + 1.
rm_crashed(RM, T + 1) :- rm_crashed(RM, T), time(T), time(T + 1).
% Rule: r_22e408788ea7  |  line_index: 6  |  NL: If the transaction manager has crashed at time step T, then the transaction manager has crashed at time step T + 1.
tm_crashed(TM, T + 1) :- tm_crashed(TM, T), time(T), time(T + 1).
% Rule: r_5e917500a5e4  |  line_index: 7  |  NL: If a resource manager is in the working state at time step T and has not crashed at time step T, then exactly one of the following holds at time step T + 1: the resource manager is in the working state, the resource manager is in the prepared state, or the resource manager is in the aborted state.
1 { rm_state(RM, working, T + 1); rm_state(RM, prepared, T + 1); rm_state(RM, aborted, T + 1) } 1 :- rm_state(RM, working, T), -rm_crashed(RM, T), time(T), time(T + 1).
% Rule: r_03c1d93eeca5  |  line_index: 8  |  NL: If a resource manager is in the working state at time step T and is in the prepared state at time step T + 1, then exactly one prepared message from that resource manager is sent at time step T + 1.
1 { sent_prepared(RM, T + 1) } 1 :- rm_state(RM, working, T), rm_state(RM, prepared, T + 1), time(T), time(T + 1).
% Rule: r_37f3f5a041c3  |  line_index: 9  |  NL: If a resource manager is in the working state at time step T and is in the aborted state at time step T + 1, then exactly one abort vote message from that resource manager is sent at time step T + 1.
1 { sent_abort_vote(RM, T + 1) } 1 :- rm_state(RM, working, T), rm_state(RM, aborted, T + 1), time(T), time(T + 1).
% Rule: r_58af1929cdf0  |  line_index: 0  |  NL: The transaction manager has received a prepared vote from a specific resource manager at time T if a prepared message from that specific resource manager was sent at any time less than or equal to T.
tm_received_prepared(RM, T) :- sent_prepared(RM, T1), T1 <= T, resource_manager(RM), time(T), time(T1).
% Rule: r_193be997830b  |  line_index: 1  |  NL: The transaction manager has received an abort vote from a specific resource manager at time T if an abort vote message from that specific resource manager was sent at any time less than or equal to T.
tm_received_abort_vote(RM, T) :- sent_abort_vote(RM, T1), T1 <= T, resource_manager(RM), time(T), time(T1).
% Rule: r_6e27c2d3a86b  |  line_index: 2  |  NL: If the transaction manager is in the init state at time T and the transaction manager has not crashed at time T, then the transaction manager is in the collecting state at time T plus 1.
tm_state(TM, collecting, T + 1) :- tm_state(TM, init, T), -tm_crashed(TM, T), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_539a33f12811  |  line_index: 3  |  NL: If the transaction manager is in the collecting state at time T, the transaction manager has received a prepared vote from resource manager rm1 at time T, the transaction manager has received a prepared vote from resource manager rm2 at time T, the transaction manager has received a prepared vote from resource manager rm3 at time T, and the transaction manager has not crashed at time T, then the transaction manager is in the committed state at time T plus 1.
tm_state(TM, committed, T + 1) :- tm_state(TM, collecting, T), tm_received_prepared(rm1, T), tm_received_prepared(rm2, T), tm_received_prepared(rm3, T), -tm_crashed(TM, T), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_1efddc583aa2  |  line_index: 4  |  NL: If the transaction manager is in the collecting state at time T, the transaction manager has received an abort vote from at least one resource manager at time T, and the transaction manager has not crashed at time T, then the transaction manager is in the aborted state at time T plus 1.
tm_state(TM, aborted, T + 1) :- tm_state(TM, collecting, T), tm_received_abort_vote(RM, T), -tm_crashed(TM, T), resource_manager(RM), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_1c870837a470  |  line_index: 5  |  NL: If the transaction manager is in the committed state at time T plus 1 and the transaction manager was not in the committed state at time T, then the transaction manager sends a commit message to every resource manager at time T plus 1.
sent_commit(RM, T + 1) :- tm_state(TM, committed, T + 1), not tm_state(TM, committed, T), resource_manager(RM), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_ef65166a18f0  |  line_index: 6  |  NL: If the transaction manager is in the aborted state at time T plus 1 and the transaction manager was not in the aborted state at time T, then the transaction manager sends an abort decision message to every resource manager at time T plus 1.
sent_abort_decision(RM, T + 1) :- tm_state(TM, aborted, T + 1), not tm_state(TM, aborted, T), resource_manager(RM), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_dfa0dec59934  |  line_index: 7  |  NL: A resource manager has received a commit message at time T if a commit message to that resource manager was sent at time T.
rm_received_commit(RM, T) :- sent_commit(RM, T), resource_manager(RM), time(T).
% Rule: r_8b376b44db85  |  line_index: 8  |  NL: A resource manager has received a commit message at time T if that resource manager had received a commit message at time T minus 1.
rm_received_commit(RM, T) :- rm_received_commit(RM, T - 1), resource_manager(RM), time(T), time(T - 1).
% Rule: r_4ec23266eb39  |  line_index: 9  |  NL: A resource manager has received an abort decision message at time T if an abort decision message to that resource manager was sent at time T.
rm_received_abort_decision(RM, T) :- sent_abort_decision(RM, T), resource_manager(RM), time(T).

% Bundle: nlchunk_20260426_182846Z_4c83aa82
% Rule: r_b2d6b0b20056  |  line_index: 0  |  NL: There are exactly three resource managers.
:- not { resource_manager(RM) } = 3.
% Rule: r_81504e78700a  |  line_index: 1  |  NL: rm1 is a resource manager.
resource_manager(rm1).
% Rule: r_904b8f810556  |  line_index: 2  |  NL: rm2 is a resource manager.
resource_manager(rm2).
% Rule: r_0cb1ca807137  |  line_index: 3  |  NL: rm3 is a resource manager.
resource_manager(rm3).
% Rule: r_9a7062a802a8  |  line_index: 4  |  NL: There is exactly one transaction manager.
:- not { transaction_manager(TM) } = 1.
% Rule: r_d6562ce342b6  |  line_index: 5  |  NL: tm is a transaction manager.
transaction_manager(tm).
% Rule: r_ac748d4ff3c6  |  line_index: 6  |  NL: Time proceeds in discrete steps numbered 0 through 12.
time(0..12).
% Rule: r_9ea13ebeec66  |  line_index: 7  |  NL: Every resource manager is in exactly one state at any given time step.
1 { rm_state(RM, S, T) : state_type_rm(S) } 1 :- resource_manager(RM), time(T).
% Rule: r_c31408db0c86  |  line_index: 8  |  NL: Every resource manager state must be one of: working, prepared, committed, or aborted.
state_type_rm(working).
state_type_rm(prepared).
state_type_rm(committed).
state_type_rm(aborted).
% Rule: r_d1abe654a7dc  |  line_index: 9  |  NL: The transaction manager is in exactly one state at any given time step.
1 { tm_state(TM, S, T) : state_type_tm(S) } 1 :- transaction_manager(TM), time(T).
% Rule: r_cebb85dcaff5  |  line_index: 10  |  NL: The transaction manager state must be one of: init, collecting, committed, or aborted.
state_type_tm(init).
state_type_tm(collecting).
state_type_tm(committed).
state_type_tm(aborted).
% Rule: r_bc081d52621f  |  line_index: 11  |  NL: At time step 0, every resource manager is in the working state.
rm_state(RM, working, 0) :- resource_manager(RM).
% Rule: r_136e744c5e1d  |  line_index: 0  |  NL: At time step 0, the transaction manager is in the init state.
tm_state(TM, init, 0) :- transaction_manager(TM).
% Rule: r_5ac9bf2e41c3  |  line_index: 1  |  NL: At time step 0, every resource manager has not crashed.
-rm_crashed(RM, 0) :- resource_manager(RM).
% Rule: r_173546f119c6  |  line_index: 2  |  NL: At time step 0, the transaction manager has not crashed.
-tm_crashed(TM, 0) :- transaction_manager(TM).
% Rule: r_81823e114654  |  line_index: 3  |  NL: Every resource manager either has crashed at a given time step or has not crashed at that time step.
1 { rm_crashed(RM, T); -rm_crashed(RM, T) } 1 :- resource_manager(RM), time(T).
% Rule: r_cabba388a083  |  line_index: 4  |  NL: The transaction manager either has crashed at a given time step or has not crashed at that time step.
1 { tm_crashed(TM, T); -tm_crashed(TM, T) } 1 :- transaction_manager(TM), time(T).
% Rule: r_78fd1ed2f124  |  line_index: 5  |  NL: If a resource manager has crashed at time step T, then that resource manager has crashed at time step T + 1.
rm_crashed(RM, T + 1) :- rm_crashed(RM, T), time(T), time(T + 1).
% Rule: r_22e408788ea7  |  line_index: 6  |  NL: If the transaction manager has crashed at time step T, then the transaction manager has crashed at time step T + 1.
tm_crashed(TM, T + 1) :- tm_crashed(TM, T), time(T), time(T + 1).
% Rule: r_5e917500a5e4  |  line_index: 7  |  NL: If a resource manager is in the working state at time step T and has not crashed at time step T, then exactly one of the following holds at time step T + 1: the resource manager is in the working state, the resource manager is in the prepared state, or the resource manager is in the aborted state.
1 { rm_state(RM, working, T + 1); rm_state(RM, prepared, T + 1); rm_state(RM, aborted, T + 1) } 1 :- rm_state(RM, working, T), -rm_crashed(RM, T), time(T), time(T + 1).
% Rule: r_03c1d93eeca5  |  line_index: 8  |  NL: If a resource manager is in the working state at time step T and is in the prepared state at time step T + 1, then exactly one prepared message from that resource manager is sent at time step T + 1.
1 { sent_prepared(RM, T + 1) } 1 :- rm_state(RM, working, T), rm_state(RM, prepared, T + 1), time(T), time(T + 1).
% Rule: r_37f3f5a041c3  |  line_index: 9  |  NL: If a resource manager is in the working state at time step T and is in the aborted state at time step T + 1, then exactly one abort vote message from that resource manager is sent at time step T + 1.
1 { sent_abort_vote(RM, T + 1) } 1 :- rm_state(RM, working, T), rm_state(RM, aborted, T + 1), time(T), time(T + 1).
% Rule: r_58af1929cdf0  |  line_index: 0  |  NL: The transaction manager has received a prepared vote from a specific resource manager at time T if a prepared message from that specific resource manager was sent at any time less than or equal to T.
tm_received_prepared(RM, T) :- sent_prepared(RM, T1), T1 <= T, resource_manager(RM), time(T), time(T1).
% Rule: r_193be997830b  |  line_index: 1  |  NL: The transaction manager has received an abort vote from a specific resource manager at time T if an abort vote message from that specific resource manager was sent at any time less than or equal to T.
tm_received_abort_vote(RM, T) :- sent_abort_vote(RM, T1), T1 <= T, resource_manager(RM), time(T), time(T1).
% Rule: r_6e27c2d3a86b  |  line_index: 2  |  NL: If the transaction manager is in the init state at time T and the transaction manager has not crashed at time T, then the transaction manager is in the collecting state at time T plus 1.
tm_state(TM, collecting, T + 1) :- tm_state(TM, init, T), -tm_crashed(TM, T), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_539a33f12811  |  line_index: 3  |  NL: If the transaction manager is in the collecting state at time T, the transaction manager has received a prepared vote from resource manager rm1 at time T, the transaction manager has received a prepared vote from resource manager rm2 at time T, the transaction manager has received a prepared vote from resource manager rm3 at time T, and the transaction manager has not crashed at time T, then the transaction manager is in the committed state at time T plus 1.
tm_state(TM, committed, T + 1) :- tm_state(TM, collecting, T), tm_received_prepared(rm1, T), tm_received_prepared(rm2, T), tm_received_prepared(rm3, T), -tm_crashed(TM, T), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_1efddc583aa2  |  line_index: 4  |  NL: If the transaction manager is in the collecting state at time T, the transaction manager has received an abort vote from at least one resource manager at time T, and the transaction manager has not crashed at time T, then the transaction manager is in the aborted state at time T plus 1.
tm_state(TM, aborted, T + 1) :- tm_state(TM, collecting, T), tm_received_abort_vote(RM, T), -tm_crashed(TM, T), resource_manager(RM), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_1c870837a470  |  line_index: 5  |  NL: If the transaction manager is in the committed state at time T plus 1 and the transaction manager was not in the committed state at time T, then the transaction manager sends a commit message to every resource manager at time T plus 1.
sent_commit(RM, T + 1) :- tm_state(TM, committed, T + 1), not tm_state(TM, committed, T), resource_manager(RM), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_ef65166a18f0  |  line_index: 6  |  NL: If the transaction manager is in the aborted state at time T plus 1 and the transaction manager was not in the aborted state at time T, then the transaction manager sends an abort decision message to every resource manager at time T plus 1.
sent_abort_decision(RM, T + 1) :- tm_state(TM, aborted, T + 1), not tm_state(TM, aborted, T), resource_manager(RM), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_dfa0dec59934  |  line_index: 7  |  NL: A resource manager has received a commit message at time T if a commit message to that resource manager was sent at time T.
rm_received_commit(RM, T) :- sent_commit(RM, T), resource_manager(RM), time(T).
% Rule: r_8b376b44db85  |  line_index: 8  |  NL: A resource manager has received a commit message at time T if that resource manager had received a commit message at time T minus 1.
rm_received_commit(RM, T) :- rm_received_commit(RM, T - 1), resource_manager(RM), time(T), time(T - 1).
% Rule: r_4ec23266eb39  |  line_index: 9  |  NL: A resource manager has received an abort decision message at time T if an abort decision message to that resource manager was sent at time T.
rm_received_abort_decision(RM, T) :- sent_abort_decision(RM, T), resource_manager(RM), time(T).
% Rule: r_928a621291c1  |  line_index: 0  |  NL: Every resource manager has received an abort decision message at time T if that resource manager had received an abort decision message at time T minus 1.
rm_received_abort_decision(RM, T) :- rm_received_abort_decision(RM, T - 1), resource_manager(RM), time(T), time(T - 1).
% Rule: r_918e0fb6f1d8  |  line_index: 1  |  NL: If a resource manager is in the prepared state at time T, has received a commit message at time T, and has not crashed at time T, then that resource manager is in the committed state at time T plus 1.
rm_state(RM, committed, T + 1) :- rm_state(RM, prepared, T), rm_received_commit(RM, T), -rm_crashed(RM, T), resource_manager(RM), time(T), time(T + 1).
% Rule: r_b56464bc745d  |  line_index: 2  |  NL: If a resource manager is in the prepared state at time T, has received an abort decision message at time T, and has not crashed at time T, then that resource manager is in the aborted state at time T plus 1.
rm_state(RM, aborted, T + 1) :- rm_state(RM, prepared, T), rm_received_abort_decision(RM, T), -rm_crashed(RM, T), resource_manager(RM), time(T), time(T + 1).
% Rule: r_bc341fac5c6c  |  line_index: 3  |  NL: If a resource manager is in the prepared state at time T, has not received a commit message at time T, has not received an abort decision message at time T, and has not crashed at time T, then that resource manager is in the prepared state at time T plus 1.
rm_state(RM, prepared, T + 1) :- rm_state(RM, prepared, T), not rm_received_commit(RM, T), not rm_received_abort_decision(RM, T), -rm_crashed(RM, T), resource_manager(RM), time(T), time(T + 1).
% Rule: r_9c4b8e4a21cd  |  line_index: 4  |  NL: If a resource manager is in the committed state at time T, then that resource manager is in the committed state at time T plus 1.
rm_state(RM, committed, T + 1) :- rm_state(RM, committed, T), resource_manager(RM), time(T), time(T + 1).
% Rule: r_7d55ae22e570  |  line_index: 5  |  NL: If a resource manager is in the aborted state at time T, then that resource manager is in the aborted state at time T plus 1.
rm_state(RM, aborted, T + 1) :- rm_state(RM, aborted, T), resource_manager(RM), time(T), time(T + 1).
% Rule: r_fc99180285ef  |  line_index: 6  |  NL: If the transaction manager is in the committed state at time T, then the transaction manager is in the committed state at time T plus 1.
tm_state(TM, committed, T + 1) :- tm_state(TM, committed, T), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_ce3ae42e3a80  |  line_index: 7  |  NL: If the transaction manager is in the aborted state at time T, then the transaction manager is in the aborted state at time T plus 1.
tm_state(TM, aborted, T + 1) :- tm_state(TM, aborted, T), transaction_manager(TM), time(T), time(T + 1).
% Rule: r_0523e3541ad5  |  line_index: 8  |  NL: If a resource manager has crashed at time T and is in state S at time T, then that resource manager is in state S at time T plus 1.
rm_state(RM, S, T + 1) :- rm_crashed(RM, T), rm_state(RM, S, T), state_type_rm(S), resource_manager(RM), time(T), time(T + 1).
% Rule: r_5775bd051bb7  |  line_index: 9  |  NL: If the transaction manager has crashed at time T and is in state S at time T, then the transaction manager is in state S at time T plus 1.
tm_state(TM, S, T + 1) :- tm_crashed(TM, T), tm_state(TM, S, T), state_type_tm(S), transaction_manager(TM), time(T), time(T + 1).