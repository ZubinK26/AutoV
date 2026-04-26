% Bundle: symtex_batch_20260423_180609Z_f7408c49
% Rule: r_9fbec0d31cbc  |  line_index: 0  |  NL: The relationship trotter(Carrie, Jennifer, Donald) is explicitly false.
-trotter(carrie, jennifer, donald).
% Rule: r_35ec507f294d  |  line_index: 1  |  NL: The relationship beef_loin(Carrie, Jennifer, Donald) is explicitly false.
-beef_loin(carrie, jennifer, donald).
% Rule: r_9a811204a70b  |  line_index: 2  |  NL: The relationship ruminant(Carrie, Jennifer, Donald) is true.
ruminant(carrie, jennifer, donald).
% Rule: r_7939cf663a3c  |  line_index: 3  |  NL: The relationship ewe(Carrie, Jennifer, Donald) is true.
ewe(carrie, jennifer, donald).
% Rule: r_4b2915cb3fb0  |  line_index: 4  |  NL: The relationship ground_beef(Carrie, Jennifer, Donald) is explicitly false.
-ground_beef(carrie, jennifer, donald).
% Rule: r_6a8e3743bcca  |  line_index: 5  |  NL: The relationship antelope(Carrie, Jennifer, Donald) is true.
antelope(carrie, jennifer, donald).
% Rule: r_bcba8271f913  |  line_index: 6  |  NL: The relationship tank(Derrick, Carrie, Donald) is true.
tank(derrick, carrie, donald).
% Rule: r_3b590e1b2c2b  |  line_index: 7  |  NL: The relationship bucket(Derrick, Carrie, Donald) is explicitly false.
-bucket(derrick, carrie, donald).
% Rule: r_7b1115c02c30  |  line_index: 8  |  NL: The relationship mouthful(Derrick, Carrie, Donald) is explicitly false.
-mouthful(derrick, carrie, donald).
% Rule: r_3e7f575d3fd9  |  line_index: 9  |  NL: The property vagina(Nicholas) is explicitly false.
-vagina(nicholas).
% Rule: r_b3a04f5f9df9  |  line_index: 10  |  NL: The relationship property(Derrick, Donald, Nicholas) is true.
property(derrick, donald, nicholas).
% Rule: r_c5cf85f4fa37  |  line_index: 11  |  NL: The relationship extent(Carrie, Jennifer, Donald) is true.
extent(carrie, jennifer, donald).
% Rule: r_482f844e478f  |  line_index: 12  |  NL: If goat(V3) is true and antelope(V1, V2, V3) is true, then bovid(V1, V2, V3) is explicitly false.
-bovid(V1, V2, V3) :- goat(V3), antelope(V1, V2, V3).
% Rule: r_3038be3b69b6  |  line_index: 13  |  NL: If trotter(V1, V2, V3) is explicitly false, and there is no evidence that ruminant(V1, V2, V3) is explicitly false, and there is no evidence that ewe(V1, V2, V3) is explicitly false, and there is no evidence that ground_beef(V1, V2, V3) is true, and there is no evidence that antelope(V1, V2, V3) is explicitly false, then sheep(V3, V1, V3) is true.
sheep(V3, V1, V3) :- -trotter(V1, V2, V3), not -ruminant(V1, V2, V3), not -ewe(V1, V2, V3), not ground_beef(V1, V2, V3), not -antelope(V1, V2, V3).
% Rule: r_dc88b9a53c78  |  line_index: 14  |  NL: If trotter(V1, V2, V3) is explicitly false, and there is no evidence that ruminant(V1, V2, V3) is explicitly false, and there is no evidence that ewe(V1, V2, V3) is explicitly false, and there is no evidence that ground_beef(V1, V2, V3) is true, and there is no evidence that antelope(V1, V2, V3) is explicitly false, then ox(V3) is explicitly false.
-ox(V3) :- -trotter(V1, V2, V3), not -ruminant(V1, V2, V3), not -ewe(V1, V2, V3), not ground_beef(V1, V2, V3), not -antelope(V1, V2, V3).
% Rule: r_14afbdca607f  |  line_index: 15  |  NL: If sheep(V0, V1, V3) is true and there is no evidence that containerful(V0, V1, V3) is true, then goat(V3) is true.
goat(V3) :- sheep(V0, V1, V3), not containerful(V0, V1, V3).
% Rule: r_43728b6d22f1  |  line_index: 16  |  NL: If indefinite_quantity(V3) is true, and bovine(V4) is true, and vagina(V4) is explicitly false, and property(V0, V3, V4) is true, and extent(V1, V2, V3) is true, then teacup(V0, V1, V3) is true.
teacup(V0, V1, V3) :- indefinite_quantity(V3), bovine(V4), -vagina(V4), property(V0, V3, V4), extent(V1, V2, V3).
% Rule: r_5e6c46aa0588  |  line_index: 17  |  NL: If teacup(V0, V1, V3) is true, and there is no evidence that can(V0, V1, V3) is true, and there is no evidence that tank(V0, V1, V3) is explicitly false, and there is no evidence that bucket(V0, V1, V3) is true, and there is no evidence that mouthful(V0, V1, V3) is true, then containerful(V0, V1, V3) is explicitly false.
-containerful(V0, V1, V3) :- teacup(V0, V1, V3), not can(V0, V1, V3), not -tank(V0, V1, V3), not bucket(V0, V1, V3), not mouthful(V0, V1, V3).
% Rule: r_0e8811dec79b  |  line_index: 18  |  NL: If beef_loin(V1, V2, V3) is explicitly false and there is no evidence that ground_beef(V1, V2, V3) is true, then beef(V2) is explicitly false.
-beef(V2) :- -beef_loin(V1, V2, V3), not ground_beef(V1, V2, V3).
% Rule: r_d07ec707a557  |  line_index: 19  |  NL: If beef_loin(V1, V2, V3) is explicitly false and there is no evidence that ground_beef(V1, V2, V3) is true, then indefinite_quantity(V3) is true.
indefinite_quantity(V3) :- -beef_loin(V1, V2, V3), not ground_beef(V1, V2, V3).
% Rule: r_585dfc8b3b43  |  line_index: 20  |  NL: If beef(V0) is explicitly false, then can(V0, V0, V0) is explicitly false.
-can(V0, V0, V0) :- -beef(V0).
% Rule: r_ac6809f1058f  |  line_index: 21  |  NL: If beef(V0) is explicitly false, then cattle(V0, V0, V0) is true.
cattle(V0, V0, V0) :- -beef(V0).
% Rule: r_dd341f949bfc  |  line_index: 22  |  NL: If ox(V3) is explicitly false, and indefinite_quantity(V3) is true, and cattle(V0, V3, V4) is true, then bovine(V4) is true.
bovine(V4) :- -ox(V3), indefinite_quantity(V3), cattle(V0, V3, V4).