% Bundle: symtex_batch_20260423_180609Z_f7408c49

person(carrie). person(jennifer). person(donald). person(derrick). person(nicholas).
person(X) :- person_v(X).
person_v(V0) :- sheep(V0, V1, V3).
person_v(V1) :- sheep(V0, V1, V3).
person_v(V3) :- sheep(V0, V1, V3).
person_v(V3) :- goat(V3).
person_v(V1) :- antelope(V1, V2, V3).
person_v(V2) :- antelope(V1, V2, V3).
person_v(V3) :- antelope(V1, V2, V3).
person_v(V1) :- trotter(V1, V2, V3).
person_v(V2) :- trotter(V1, V2, V3).
person_v(V3) :- trotter(V1, V2, V3).
person_v(V1) :- ruminant(V1, V2, V3).
person_v(V2) :- ruminant(V1, V2, V3).
person_v(V3) :- ruminant(V1, V2, V3).
person_v(V1) :- ewe(V1, V2, V3).
person_v(V2) :- ewe(V1, V2, V3).
person_v(V3) :- ewe(V1, V2, V3).
person_v(V1) :- ground_beef(V1, V2, V3).
person_v(V2) :- ground_beef(V1, V2, V3).
person_v(V3) :- ground_beef(V1, V2, V3).
person_v(V3) :- ox(V3).
person_v(V0) :- containerful(V0, V1, V3).
person_v(V1) :- containerful(V0, V1, V3).
person_v(V3) :- containerful(V0, V1, V3).
person_v(V3) :- indefinite_quantity(V3).
person_v(V4) :- bovine(V4).
person_v(V4) :- vagina(V4).
person_v(V0) :- property(V0, V3, V4).
person_v(V3) :- property(V0, V3, V4).
person_v(V4) :- property(V0, V3, V4).
person_v(V1) :- extent(V1, V2, V3).
person_v(V2) :- extent(V1, V2, V3).
person_v(V3) :- extent(V1, V2, V3).
person_v(V0) :- teacup(V0, V1, V3).
person_v(V1) :- teacup(V0, V1, V3).
person_v(V3) :- teacup(V0, V1, V3).
person_v(V0) :- can(V0, V1, V3).
person_v(V1) :- can(V0, V1, V3).
person_v(V3) :- can(V0, V1, V3).
person_v(V0) :- tank(V0, V1, V3).
person_v(V1) :- tank(V0, V1, V3).
person_v(V3) :- tank(V0, V1, V3).
person_v(V0) :- bucket(V0, V1, V3).
person_v(V1) :- bucket(V0, V1, V3).
person_v(V3) :- bucket(V0, V1, V3).
person_v(V0) :- mouthful(V0, V1, V3).
person_v(V1) :- mouthful(V0, V1, V3).
person_v(V3) :- mouthful(V0, V1, V3).
person_v(V1) :- beef_loin(V1, V2, V3).
person_v(V2) :- beef_loin(V1, V2, V3).
person_v(V3) :- beef_loin(V1, V2, V3).
person_v(V2) :- beef(V2).
person_v(V0) :- beef(V0).
person_v(V0) :- cattle(V0, V3, V4).
person_v(V3) :- cattle(V0, V3, V4).
person_v(V4) :- cattle(V0, V3, V4).

% Rule: r_4d4478ce56c6  |  line_index: 0  |  NL: The relationship trotter(Carrie, Jennifer, Donald) is explicitly false.
-trotter(carrie, jennifer, donald).

% Rule: r_47b0dc8fe99b  |  line_index: 1  |  NL: The relationship beef_loin(Carrie, Jennifer, Donald) is explicitly false.
-beef_loin(carrie, jennifer, donald).

% Rule: r_13ad61c0ba08  |  line_index: 2  |  NL: The relationship ruminant(Carrie, Jennifer, Donald) is true.
ruminant(carrie, jennifer, donald).

% Rule: r_4d26cf0877b3  |  line_index: 3  |  NL: The relationship ewe(Carrie, Jennifer, Donald) is true.
ewe(carrie, jennifer, donald).

% Rule: r_fa5d6a433492  |  line_index: 4  |  NL: The relationship ground_beef(Carrie, Jennifer, Donald) is explicitly false.
-ground_beef(carrie, jennifer, donald).

% Rule: r_81015c2c5d53  |  line_index: 5  |  NL: The relationship antelope(Carrie, Jennifer, Donald) is true.
antelope(carrie, jennifer, donald).

% Rule: r_000acf08a2ae  |  line_index: 6  |  NL: The relationship tank(Derrick, Carrie, Donald) is true.
tank(derrick, carrie, donald).

% Rule: r_491353d1a0b7  |  line_index: 7  |  NL: The relationship bucket(Derrick, Carrie, Donald) is explicitly false.
-bucket(derrick, carrie, donald).

% Rule: r_2936ea43fafe  |  line_index: 8  |  NL: The relationship mouthful(Derrick, Carrie, Donald) is explicitly false.
-mouthful(derrick, carrie, donald).

% Rule: r_165e647fa9fa  |  line_index: 9  |  NL: The property vagina(Nicholas) is explicitly false.
-vagina(nicholas).

% Rule: r_501ce3bdc96c  |  line_index: 10  |  NL: The relationship property(Derrick, Donald, Nicholas) is true.
property(derrick, donald, nicholas).

% Rule: r_f8a578543199  |  line_index: 11  |  NL: The relationship extent(Carrie, Jennifer, Donald) is true.
extent(carrie, jennifer, donald).

% Rule: r_9613154cdee0  |  line_index: 12  |  NL: If goat(V3) is true and antelope(V1, V2, V3) is true, then bovid(V1, V2, V3) is explicitly false.
-bovid(V1, V2, V3) :- goat(V3), antelope(V1, V2, V3), person(V1), person(V2), person(V3).

% Rule: r_d4a62739d878  |  line_index: 13  |  NL: If trotter(V1, V2, V3) is explicitly false, and there is no evidence that ruminant(V1, V2, V3) is explicitly false, and there is no evidence that ewe(V1, V2, V3) is explicitly false, and there is no evidence that ground_beef(V1, V2, V3) is true, and there is no evidence that antelope(V1, V2, V3) is explicitly false, then sheep(V3, V1, V3) is true.
sheep(V3, V1, V3) :- -trotter(V1, V2, V3), not -ruminant(V1, V2, V3), not -ewe(V1, V2, V3), not ground_beef(V1, V2, V3), not -antelope(V1, V2, V3), person(V1), person(V2), person(V3).

% Rule: r_987c7ad66a26  |  line_index: 14  |  NL: If trotter(V1, V2, V3) is explicitly false, and there is no evidence that ruminant(V1, V2, V3) is explicitly false, and there is no evidence that ewe(V1, V2, V3) is explicitly false, and there is no evidence that ground_beef(V1, V2, V3) is true, and there is no evidence that antelope(V1, V2, V3) is explicitly false, then ox(V3) is explicitly false.
-ox(V3) :- -trotter(V1, V2, V3), not -ruminant(V1, V2, V3), not -ewe(V1, V2, V3), not ground_beef(V1, V2, V3), not -antelope(V1, V2, V3), person(V1), person(V2), person(V3).

% Rule: r_3c2366849a05  |  line_index: 15  |  NL: If sheep(V0, V1, V3) is true and there is no evidence that containerful(V0, V1, V3) is true, then goat(V3) is true.
goat(V3) :- sheep(V0, V1, V3), not containerful(V0, V1, V3), person(V0), person(V1), person(V3).

% Rule: r_f64d89c332b3  |  line_index: 16  |  NL: If indefinite_quantity(V3) is true, and bovine(V4) is true, and vagina(V4) is explicitly false, and property(V0, V3, V4) is true, and extent(V1, V2, V3) is true, then teacup(V0, V1, V3) is true.
teacup(V0, V1, V3) :- indefinite_quantity(V3), bovine(V4), -vagina(V4), property(V0, V3, V4), extent(V1, V2, V3), person(V0), person(V1), person(V2), person(V3), person(V4).

% Rule: r_0a3a4a18130e  |  line_index: 17  |  NL: If teacup(V0, V1, V3) is true, and there is no evidence that can(V0, V1, V3) is true, and there is no evidence that tank(V0, V1, V3) is explicitly false, and there is no evidence that bucket(V0, V1, V3) is true, and there is no evidence that mouthful(V0, V1, V3) is true, then containerful(V0, V1, V3) is explicitly false.
-containerful(V0, V1, V3) :- teacup(V0, V1, V3), not can(V0, V1, V3), not -tank(V0, V1, V3), not bucket(V0, V1, V3), not mouthful(V0, V1, V3), person(V0), person(V1), person(V3).

% Rule: r_b93ef9183d93  |  line_index: 18  |  NL: If beef_loin(V1, V2, V3) is explicitly false and there is no evidence that ground_beef(V1, V2, V3) is true, then beef(V2) is explicitly false.
-beef(V2) :- -beef_loin(V1, V2, V3), not ground_beef(V1, V2, V3), person(V1), person(V2), person(V3).

% Rule: r_5dd30c19f8a0  |  line_index: 19  |  NL: If beef_loin(V1, V2, V3) is explicitly false and there is no evidence that ground_beef(V1, V2, V3) is true, then indefinite_quantity(V3) is true.
indefinite_quantity(V3) :- -beef_loin(V1, V2, V3), not ground_beef(V1, V2, V3), person(V1), person(V2), person(V3).

% Rule: r_7b8e1c4aa148  |  line_index: 20  |  NL: If beef(V0) is explicitly false, then can(V0, V0, V0) is explicitly false.
-can(V0, V0, V0) :- -beef(V0), person(V0).

% Rule: r_0a996e01cfd6  |  line_index: 21  |  NL: If beef(V0) is explicitly false, then cattle(V0, V0, V0) is true.
cattle(V0, V0, V0) :- -beef(V0), person(V0).

% Rule: r_d105849b34e9  |  line_index: 22  |  NL: If ox(V3) is explicitly false, and indefinite_quantity(V3) is true, and cattle(V0, V3, V4) is true, then bovine(V4) is true.
bovine(V4) :- -ox(V3), indefinite_quantity(V3), cattle(V0, V3, V4), person(V0), person(V3), person(V4).