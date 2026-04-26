% Bundle: symtex_batch_20260423_180522Z_8c01e0f8

% Domains
person(sarah).
person(nicole).
person(claire).
person(lindsey).
person(V0) :- person(V0).
person(V1) :- person(V1).
person(V2) :- person(V2).
person(V3) :- person(V3).

% Rule: r_7fd72393ca89  |  line_index: 0  |  NL: It is explicitly false that Sarah is a cavy of Nicole.
-cavy(sarah, nicole).

% Rule: r_4143a16c10ab  |  line_index: 1  |  NL: It is explicitly false that Claire sleeps with Lindsey.
-sleeps_with(claire, lindsey).

% Rule: r_ca2297b297a4  |  line_index: 2  |  NL: Lindsey is an agent of Nicole.
agent(lindsey, nicole).

% Rule: r_463af2d960a0  |  line_index: 3  |  NL: Lindsey is a bird of Sarah.
bird(lindsey, sarah).

% Rule: r_3709fd52f8e5  |  line_index: 4  |  NL: Claire is a crow of Lindsey.
crow(claire, lindsey).

% Rule: r_cc3109ffc55d  |  line_index: 5  |  NL: Sarah is a dressing sack of Nicole.
dressing_sack(sarah, nicole).

% Rule: r_9858405653f5  |  line_index: 6  |  NL: Sarah is a fish of Nicole.
fish(sarah, nicole).

% Rule: r_06fcb287f464  |  line_index: 7  |  NL: Claire is a halitus of Sarah.
halitus(claire, sarah).

% Rule: r_8fbd7fc0dcb2  |  line_index: 8  |  NL: Lindsey is a kite of Sarah.
kite(lindsey, sarah).

% Rule: r_f5b0d4c98430  |  line_index: 9  |  NL: Sarah is a little office of Nicole.
little_office(sarah, nicole).

% Rule: r_addd3e577398  |  line_index: 10  |  NL: Claire has the property of sex.
sex(claire).

% Rule: r_851db14611ed  |  line_index: 11  |  NL: Claire has the property of singing.
singing(claire).

% Rule: r_f1312ea08a3b  |  line_index: 12  |  NL: If V1 is a fly of V2 and it is explicitly false that V2 is an activity of V3, then it is explicitly false that V1 has the property of action.
-action(V1) :- fly(V1, V2), -activity(V2, V3), person(V1), person(V2), person(V3).

% Rule: r_db9d796d9057  |  line_index: 13  |  NL: If V0 has the property of sex, V0 has the property of singing, it is explicitly false that V0 sleeps with V1, V0 is a halitus of V2, and V1 is an agent of V3, then it is explicitly false that V1 is a breath of V2, or it is explicitly false that V2 is an activity of V3, or V0 has the property of feel good.
-breath(V1, V2) | -activity(V2, V3) | feel_good(V0) :- sex(V0), singing(V0), -sleeps_with(V0, V1), halitus(V0, V2), agent(V1, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_e2f05b870fa4  |  line_index: 14  |  NL: If V1 is a bird of V2 and there is no evidence that V1 is explicitly false to be a kite of V2, then it is explicitly false that V2 has the property of flying, or V1 is a fly of V2.
-flying(V2) | fly(V1, V2) :- bird(V1, V2), not -kite(V1, V2), person(V1), person(V2).

% Rule: r_0793a3a6b7d2  |  line_index: 15  |  NL: If V1 is a bat of V2, V0 has the property of feel good, V1 is a bed of V3, there is no evidence that V0 has the property of owl, and there is no evidence that V0 sleeps with V1, then it is explicitly false that V0 is a night of V3.
-night(V0, V3) :- bat(V1, V2), feel_good(V0), bed(V1, V3), not owl(V0), not sleeps_with(V0, V1), person(V0), person(V1), person(V2), person(V3).

% Rule: r_55ce692b98dd  |  line_index: 16  |  NL: If V2 is a gobbet of V3, there is no evidence that V2 is a cavy of V3, there is no evidence that it is explicitly false that V2 is a fish of V3, there is no evidence that it is explicitly false that V2 is a little office of V3, and there is no evidence that it is explicitly false that V2 is a dressing sack of V3, then it is explicitly false that V3 has the property of owl.
-owl(V3) :- gobbet(V2, V3), not cavy(V2, V3), not -fish(V2, V3), not -little_office(V2, V3), not -dressing_sack(V2, V3), person(V2), person(V3).

% Rule: r_d46b5c706b07  |  line_index: 17  |  NL: If it is explicitly false that V2 has the property of flying, it is explicitly false that V1 is a breath of V2, and there is no evidence that V1 is explicitly false to be a kite of V2, then it is explicitly false that V1 has the property of scratching, or V1 is a bat of V2, or V2 is a gobbet of V2.
-scratching(V1) | bat(V1, V2) | gobbet(V2, V2) :- -flying(V2), -breath(V1, V2), not -kite(V1, V2), person(V1), person(V2).

% Rule: r_3cde05a6e9f9  |  line_index: 18  |  NL: If it is explicitly false that V1 has the property of scratching, it is explicitly false that V1 is a breath of V2, and there is no evidence that V1 has the property of action, then V1 is a bed of V1.
bed(V1, V1) :- -scratching(V1), -breath(V1, V2), not action(V1), person(V1), person(V2).

% Rule: r_0f7b402d4afb  |  line_index: 19  |  NL: If V0 is a crow of V1, then V0 is a black of V1.
black(V0, V1) :- crow(V0, V1), person(V0), person(V1).

% Rule: r_41d917e3e80f  |  line_index: 20  |  NL: If V0 is a black of V1 and it is explicitly false that V0 is a night of V3, then V0 has the property of dark.
dark(V0) :- black(V0, V1), -night(V0, V3), person(V0), person(V1), person(V3).