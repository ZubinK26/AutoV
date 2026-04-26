% Bundle: symtex_batch_20260423_180522Z_8c01e0f8
% Rule: r_a8530a8e8969  |  line_index: 0  |  NL: It is explicitly false that Sarah is a cavy of Nicole.
-cavy(sarah, nicole).
% Rule: r_ddf6d96e64c1  |  line_index: 1  |  NL: It is explicitly false that Claire sleeps with Lindsey.
-sleeps_with(claire, lindsey).
% Rule: r_ec374e1cb0d5  |  line_index: 2  |  NL: Lindsey is an agent of Nicole.
agent(lindsey, nicole).
% Rule: r_8ff0ff2a77f4  |  line_index: 3  |  NL: Lindsey is a bird of Sarah.
bird(lindsey, sarah).
% Rule: r_0273c16aaf31  |  line_index: 4  |  NL: Claire is a crow of Lindsey.
crow(claire, lindsey).
% Rule: r_ccc27e045c90  |  line_index: 5  |  NL: Sarah is a dressing sack of Nicole.
dressing_sack(sarah, nicole).
% Rule: r_ce8f7bd1cfca  |  line_index: 6  |  NL: Sarah is a fish of Nicole.
fish(sarah, nicole).
% Rule: r_f8ce619544ab  |  line_index: 7  |  NL: Claire is a halitus of Sarah.
halitus(claire, sarah).
% Rule: r_1fa8e8c3e2bd  |  line_index: 8  |  NL: Lindsey is a kite of Sarah.
kite(lindsey, sarah).
% Rule: r_33392c05910f  |  line_index: 9  |  NL: Sarah is a little office of Nicole.
little_office(sarah, nicole).
% Rule: r_c8baae5e10e2  |  line_index: 10  |  NL: Claire has the property of sex.
sex(claire).
% Rule: r_175437d3725e  |  line_index: 11  |  NL: Claire has the property of singing.
singing(claire).
% Rule: r_a35ff2d7ed5f  |  line_index: 12  |  NL: If V1 is a fly of V2 and it is explicitly false that V2 is an activity of V3, then it is explicitly false that V1 has the property of action.
-action(V1) :- fly(V1, V2), -activity(V2, V3).
% Rule: r_4ec093a4a926  |  line_index: 13  |  NL: If V0 has the property of sex, V0 has the property of singing, it is explicitly false that V0 sleeps with V1, V0 is a halitus of V2, and V1 is an agent of V3, then it is explicitly false that V1 is a breath of V2, or it is explicitly false that V2 is an activity of V3, or V0 has the property of feel good.
-breath(V1, V2) | -activity(V2, V3) | feel_good(V0) :- sex(V0), singing(V0), -sleeps_with(V0, V1), halitus(V0, V2), agent(V1, V3).
% Rule: r_8b6b169a93fa  |  line_index: 14  |  NL: If V1 is a bird of V2 and there is no evidence that V1 is explicitly false to be a kite of V2, then it is explicitly false that V2 has the property of flying, or V1 is a fly of V2.
-flying(V2) | fly(V1, V2) :- bird(V1, V2), not -kite(V1, V2).
% Rule: r_14db4dfaf633  |  line_index: 15  |  NL: If V1 is a bat of V2, V0 has the property of feel good, V1 is a bed of V3, there is no evidence that V0 has the property of owl, and there is no evidence that V0 sleeps with V1, then it is explicitly false that V0 is a night of V3.
-night(V0, V3) :- bat(V1, V2), feel_good(V0), bed(V1, V3), not owl(V0), not sleeps_with(V0, V1).
% Rule: r_4db757dea601  |  line_index: 16  |  NL: If V2 is a gobbet of V3, there is no evidence that V2 is a cavy of V3, there is no evidence that it is explicitly false that V2 is a fish of V3, there is no evidence that it is explicitly false that V2 is a little office of V3, and there is no evidence that it is explicitly false that V2 is a dressing sack of V3, then it is explicitly false that V3 has the property of owl.
-owl(V3) :- gobbet(V2, V3), not cavy(V2, V3), not -fish(V2, V3), not -little_office(V2, V3), not -dressing_sack(V2, V3).
% Rule: r_d7d228e76dc3  |  line_index: 17  |  NL: If it is explicitly false that V2 has the property of flying, it is explicitly false that V1 is a breath of V2, and there is no evidence that V1 is explicitly false to be a kite of V2, then it is explicitly false that V1 has the property of scratching, or V1 is a bat of V2, or V2 is a gobbet of V2.
-scratching(V1) | bat(V1, V2) | gobbet(V2, V2) :- -flying(V2), -breath(V1, V2), not -kite(V1, V2).
% Rule: r_6a1928808901  |  line_index: 18  |  NL: If it is explicitly false that V1 has the property of scratching, it is explicitly false that V1 is a breath of V2, and there is no evidence that V1 has the property of action, then V1 is a bed of V1.
bed(V1, V1) :- -scratching(V1), -breath(V1, V2), not action(V1).
% Rule: r_2a35e09b566d  |  line_index: 19  |  NL: If V0 is a crow of V1, then V0 is a black of V1.
black(V0, V1) :- crow(V0, V1).
% Rule: r_8c061946e272  |  line_index: 20  |  NL: If V0 is a black of V1 and it is explicitly false that V0 is a night of V3, then V0 has the property of dark.
dark(V0) :- black(V0, V1), -night(V0, V3).