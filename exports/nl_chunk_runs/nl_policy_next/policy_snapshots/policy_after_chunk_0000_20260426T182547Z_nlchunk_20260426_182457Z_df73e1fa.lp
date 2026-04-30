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