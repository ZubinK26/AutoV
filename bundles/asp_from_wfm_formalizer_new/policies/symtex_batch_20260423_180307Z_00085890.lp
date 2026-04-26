% Bundle: symtex_batch_20260423_180307Z_00085890

% Rule: r_d5fa14ba8bcd  |  line_index: 0  |  NL: It is explicitly false that Shawn is an asthenosphere.
-asthenosphere(shawn).

% Rule: r_b9128d705a4f  |  line_index: 1  |  NL: It is explicitly false that Judy and Shawn have a black rat relationship.
-black_rat(judy, shawn).

% Rule: r_153e38a6c8fe  |  line_index: 2  |  NL: It is explicitly false that Mary and Stephanie have a corn relationship.
-corn(mary, stephanie).

% Rule: r_9b3df821ccb6  |  line_index: 3  |  NL: It is explicitly false that Stephanie and Shawn have a corncob relationship.
-corncob(stephanie, shawn).

% Rule: r_97cb277e441a  |  line_index: 4  |  NL: It is explicitly false that Mary and Stephanie have a field corn relationship.
-field_corn(mary, stephanie).

% Rule: r_7a2d463418f0  |  line_index: 5  |  NL: It is explicitly false that Judy, Ryan, and Shawn have a rota relationship.
-rota(judy, ryan, shawn).

% Rule: r_39d0eeca1629  |  line_index: 6  |  NL: It is explicitly false that Judy and Stephanie have a wear relationship.
-wear(judy, stephanie).

% Rule: r_6dbc62324075  |  line_index: 7  |  NL: It is true that Judy and Stephanie have a deal drugs relationship.
deal_drugs(judy, stephanie).

% Rule: r_04e2d3e38967  |  line_index: 8  |  NL: It is true that Ryan and Shawn have an ear relationship.
ear(ryan, shawn).

% Rule: r_0340369128c0  |  line_index: 9  |  NL: It is true that Judy and Shawn have a jerboa rat relationship.
jerboa_rat(judy, shawn).

% Rule: r_fd9dbaada87d  |  line_index: 10  |  NL: It is true that Judy and Mary have a most commonly relationship.
most_commonly(judy, mary).

% Rule: r_3626b8cefbd9  |  line_index: 11  |  NL: It is true that Judy, Ryan, and Mary have a radio operator relationship.
radio_operator(judy, ryan, mary).

% Rule: r_584c26bceb5a  |  line_index: 12  |  NL: It is true that Ryan and Mary have a sweet corn relationship.
sweet_corn(ryan, mary).

% Rule: r_832abe72a4de  |  line_index: 13  |  NL: It is true that Judy and Shawn have a swiss pine relationship.
swiss_pine(judy, shawn).

% Rule: r_ac8a3e5c2912  |  line_index: 14  |  NL: It is true that Shawn is a tropopause.
tropopause(shawn).

% Rule: r_9a1a14e72297  |  line_index: 15  |  NL: If V4 is a rice and V4 is explicitly false as a millet and V0, V1, and V2 have a barley relationship and V2, V3, and V4 have a P7 relationship, then V1 and V2 are explicitly false as a cereal.
-cereal(V1, V2) :- rice(V4), -millet(V4), barley(V0, V1, V2), p7(V2, V3, V4).

% Rule: r_da91537a583d  |  line_index: 16  |  NL: If V0 and V4 have a bandicoot rat relationship and there is no evidence that V0 and V4 are explicitly false as a rice rat and there is no evidence that V0 and V4 are explicitly false as a swiss pine and there is no evidence that V0 and V4 are explicitly false as a jerboa rat and there is no evidence that V0 and V4 have a black rat relationship, then V4 is explicitly false as a millet.
-millet(V4) :- bandicoot_rat(V0, V4), not -rice_rat(V0, V4), not -swiss_pine(V0, V4), not -jerboa_rat(V0, V4), not black_rat(V0, V4).

% Rule: r_9fbb5ff9039b  |  line_index: 17  |  NL: If V0 and V4 have a bandicoot rat relationship and there is no evidence that V0 and V4 are explicitly false as a rice rat and there is no evidence that V0 and V4 are explicitly false as a swiss pine and there is no evidence that V0 and V4 are explicitly false as a jerboa rat and there is no evidence that V0 and V4 have a black rat relationship, then V0 and V4 are explicitly false as a rat.
-rat(V0, V4) :- bandicoot_rat(V0, V4), not -rice_rat(V0, V4), not -swiss_pine(V0, V4), not -jerboa_rat(V0, V4), not black_rat(V0, V4).

% Rule: r_469ba65030c2  |  line_index: 18  |  NL: If V1 and V2 have a sweet corn relationship and V1 and V4 have an ear relationship and V2 and V3 are explicitly false as a corn and there is no evidence that V2 and V3 have a field corn relationship and there is no evidence that V3 and V4 have a corncob relationship, then V2, V3, and V4 have a P7 relationship.
p7(V2, V3, V4) :- sweet_corn(V1, V2), ear(V1, V4), -corn(V2, V3), not field_corn(V2, V3), not corncob(V3, V4).

% Rule: r_584c339efb98  |  line_index: 19  |  NL: If V0, V1, and V4 are explicitly false as a rota, then V0 and V4 have a bandicoot rat relationship.
bandicoot_rat(V0, V4) :- -rota(V0, V1, V4).

% Rule: r_853591802eed  |  line_index: 20  |  NL: If V0 and V2 have a most commonly relationship and V0 and V3 are explicitly false as a wear and V0, V1, and V2 have a radio operator relationship, then V0, V1, and V2 have a barley relationship.
barley(V0, V1, V2) :- most_commonly(V0, V2), -wear(V0, V3), radio_operator(V0, V1, V2).

% Rule: r_7caf2c91db1d  |  line_index: 21  |  NL: If V4 is explicitly false as a millet and there is no evidence that V4 is an asthenosphere, then V4 and V4 have a crust relationship.
crust(V4, V4) :- -millet(V4), not asthenosphere(V4).

% Rule: r_505db5ebb7fc  |  line_index: 22  |  NL: If V4 is explicitly false as an asthenosphere and there is no evidence that V4 is explicitly false as a tropopause, then V4, V4, and V4 have a layer relationship.
layer(V4, V4, V4) :- -asthenosphere(V4), not -tropopause(V4).

% Rule: r_14f946a767f8  |  line_index: 23  |  NL: If V1 and V3 have a crust relationship and V2 and V3 are explicitly false as a rat and V1, V3, and V4 have a layer relationship, then V4 is a rice.
rice(V4) :- crust(V1, V3), -rat(V2, V3), layer(V1, V3, V4).

% Rule: r_2800e6bb0c4d  |  line_index: 24  |  NL: If V0 and V3 have a deal drugs relationship and there is no evidence that V0 and V3 have a wear relationship, then V0 and V0 have a rice rat relationship.
rice_rat(V0, V0) :- deal_drugs(V0, V3), not wear(V0, V3).