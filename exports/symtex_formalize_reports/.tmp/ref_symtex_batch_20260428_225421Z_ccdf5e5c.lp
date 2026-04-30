- insufflation("Thomas", "Rebecca").
- stiffening("Katie", "Rebecca").
man("Thomas", "Rebecca").
play("Thomas", "Rebecca").
social_activity("Katie", "Rebecca").
- cardiac_massage(V0, V3) :- group_action(V0, V3).
- emergency_procedure(V3, V3) :- - cardiac_massage(V0, V3), not -artificial_respiration(V0, V3).
- measure(V1) :- - stiffening(V1, V3).
action(V0, V3) :- play(V0, V3).
artificial_respiration(V1, V3) :- - stiffening(V1, V3).
group_action(V0, V3) :- action(V0, V3), social_activity(V1, V3), not -man(V0, V3), not insufflation(V0, V3).
procedure(V1) :- - emergency_procedure(V2, V3), - stiffening(V1, V3), not -social_activity(V1, V3).
t_bone_steak(V1) :- - measure(V1), procedure(V1), work(V3), not -social_activity(V1, V3).
work(V3) :- action(V0, V3), social_activity(V1, V3), not -man(V0, V3), not insufflation(V0, V3).