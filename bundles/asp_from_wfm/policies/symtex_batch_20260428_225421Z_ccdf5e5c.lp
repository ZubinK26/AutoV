% Bundle: symtex_batch_20260428_225421Z_ccdf5e5c
% Rule: r_5f436f0c70f0  |  line_index: 0  |  NL: The insufflation relationship between Thomas and Rebecca is explicitly false.
-insufflation(thomas, rebecca).
% Rule: r_1460b82b027a  |  line_index: 1  |  NL: The stiffening relationship between Katie and Rebecca is explicitly false.
-stiffening(katie, rebecca).
% Rule: r_859fbc5c31d4  |  line_index: 2  |  NL: The man relationship between Thomas and Rebecca is true.
man(thomas, rebecca).
% Rule: r_18587b338b06  |  line_index: 3  |  NL: The play relationship between Thomas and Rebecca is true.
play(thomas, rebecca).
% Rule: r_83bc5287ff7f  |  line_index: 4  |  NL: The social activity relationship between Katie and Rebecca is true.
social_activity(katie, rebecca).
% Rule: r_67554b595e14  |  line_index: 5  |  NL: For any entities V0 and V3, if the group action relationship between V0 and V3 is true, then the cardiac massage relationship between V0 and V3 is explicitly false.
-cardiac_massage(V0, V3) :- group_action(V0, V3).
% Rule: r_7cbd0adb6dc6  |  line_index: 6  |  NL: For any entities V0 and V3, if the cardiac massage relationship between V0 and V3 is explicitly false and there is no evidence that the artificial respiration relationship between V0 and V3 is explicitly false, then the emergency procedure relationship between V3 and V3 is explicitly false.
-emergency_procedure(V3, V3) :- -cardiac_massage(V0, V3), not -artificial_respiration(V0, V3).
% Rule: r_9f79b3560060  |  line_index: 7  |  NL: For any entities V1 and V3, if the stiffening relationship between V1 and V3 is explicitly false, then the measure of V1 is explicitly false.
-measure(V1) :- -stiffening(V1, V3).
% Rule: r_9431d064cbd0  |  line_index: 8  |  NL: For any entities V0 and V3, if the play relationship between V0 and V3 is true, then the action relationship between V0 and V3 is true.
action(V0, V3) :- play(V0, V3).
% Rule: r_4bbde33872c0  |  line_index: 9  |  NL: For any entities V1 and V3, if the stiffening relationship between V1 and V3 is explicitly false, then the artificial respiration relationship between V1 and V3 is true.
artificial_respiration(V1, V3) :- -stiffening(V1, V3).
% Rule: r_764852ceeb5f  |  line_index: 10  |  NL: For any entities V0, V1, and V3, if the action relationship between V0 and V3 is true, the social activity relationship between V1 and V3 is true, there is no evidence that the man relationship between V0 and V3 is explicitly false, and there is no evidence that the insufflation relationship between V0 and V3 is true, then the group action relationship between V0 and V3 is true.
group_action(V0, V3) :- action(V0, V3), social_activity(V1, V3), not -man(V0, V3), not insufflation(V0, V3).
% Rule: r_252128a20bc  |  line_index: 11  |  NL: For any entities V1, V2, and V3, if the emergency procedure relationship between V2 and V3 is explicitly false, the stiffening relationship between V1 and V3 is explicitly false, and there is no evidence that the social activity relationship between V1 and V3 is explicitly false, then the procedure of V1 is true.
procedure(V1) :- -emergency_procedure(V2, V3), -stiffening(V1, V3), not -social_activity(V1, V3).
% Rule: r_440fd9480f7a  |  line_index: 12  |  NL: For any entities V1 and V3, if the measure of V1 is explicitly false, the procedure of V1 is true, the work of V3 is true, and there is no evidence that the social activity relationship between V1 and V3 is explicitly false, then the t-bone steak property of V1 is true.
t_bone_steak(V1) :- -measure(V1), procedure(V1), work(V3), not -social_activity(V1, V3).
% Rule: r_281408a79ced  |  line_index: 13  |  NL: For any entities V0, V1, and V3, if the action relationship between V0 and V3 is true, the social activity relationship between V1 and V3 is true, there is no evidence that the man relationship between V0 and V3 is explicitly false, and there is no evidence that the insufflation relationship between V0 and V3 is true, then the work of V3 is true.
work(V3) :- action(V0, V3), social_activity(V1, V3), not -man(V0, V3), not insufflation(V0, V3).