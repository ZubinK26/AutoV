- trotter("Carrie", "Jennifer", "Donald").
- beef_loin("Carrie", "Jennifer", "Donald").
ruminant("Carrie", "Jennifer", "Donald").
ewe("Carrie", "Jennifer", "Donald").
- ground_beef("Carrie", "Jennifer", "Donald").
antelope("Carrie", "Jennifer", "Donald").
tank("Derrick", "Carrie", "Donald").
- bucket("Derrick", "Carrie", "Donald").
- mouthful("Derrick", "Carrie", "Donald").
- vagina("Nicholas").
property("Derrick", "Donald", "Nicholas").
extent("Carrie", "Jennifer", "Donald").
- bovid(V1, V2, V3) :- goat(V3), antelope(V1, V2, V3).
sheep(V3, V1, V3) :- - trotter(V1, V2, V3), not -ruminant(V1, V2, V3), not -ewe(V1, V2, V3), not ground_beef(V1, V2, V3), not -antelope(V1, V2, V3).
- ox(V3) :- - trotter(V1, V2, V3), not -ruminant(V1, V2, V3), not -ewe(V1, V2, V3), not ground_beef(V1, V2, V3), not -antelope(V1, V2, V3).
goat(V3) :- sheep(V0, V1, V3), not containerful(V0, V1, V3).
teacup(V0, V1, V3) :- indefinite_quantity(V3), bovine(V4), - vagina(V4), property(V0, V3, V4), extent(V1, V2, V3).
- containerful(V0, V1, V3) :- teacup(V0, V1, V3), not can(V0, V1, V3), not -tank(V0, V1, V3), not bucket(V0, V1, V3), not mouthful(V0, V1, V3).
- beef(V2) :- - beef_loin(V1, V2, V3), not ground_beef(V1, V2, V3).
indefinite_quantity(V3) :- - beef_loin(V1, V2, V3), not ground_beef(V1, V2, V3).
- can(V0, V0, V0) :- - beef(V0).
cattle(V0, V0, V0) :- - beef(V0).
bovine(V4) :- - ox(V3), indefinite_quantity(V3), cattle(V0, V3, V4).