% Bundle: symtex_batch_20260423_180627Z_efe566e3

person(mary).
person(sabrina).
person(alison).
person(cynthia).
person(anthony).

% Rule: r_e83682fca3ed  |  line_index: 0  |  NL: It is explicitly false that Mary and Sabrina have the yellowbelly marmot relationship.
-yellowbelly_marmot(mary, sabrina).

% Rule: r_8285081de52d  |  line_index: 1  |  NL: It is explicitly false that Mary, Alison, and Cynthia have the bovine relationship.
-bovine(mary, alison, cynthia).

% Rule: r_e2d2c2ce0a59  |  line_index: 2  |  NL: It is explicitly false that Mary, Sabrina, and Anthony have the horn relationship.
-horn(mary, sabrina, anthony).

% Rule: r_6b3517af9230  |  line_index: 3  |  NL: It is true that Mary, Cynthia, and Anthony have the bullock relationship.
bullock(mary, cynthia, anthony).

% Rule: r_dbfa8d2694a4  |  line_index: 4  |  NL: It is true that Sabrina and Cynthia have the hoary marmot relationship.
hoary_marmot(sabrina, cynthia).

% Rule: r_8d64650d9808  |  line_index: 5  |  NL: It is explicitly false that Mary, Alison, and Sabrina have the sight organ relationship.
-sight_organ(mary, alison, sabrina).

% Rule: r_1e25ea14e995  |  line_index: 6  |  NL: It is explicitly false that Sabrina and Anthony have the squirrel relationship.
-squirrel(sabrina, anthony).

% Rule: r_4ace96f7aaa0  |  line_index: 7  |  NL: It is explicitly false that Cynthia and Anthony have the abrocome relationship.
-abrocome(cynthia, anthony).

% Rule: r_8d9c77721954  |  line_index: 8  |  NL: If it is explicitly false that V0, V2, and V3 have the placental relationship, then it is true that V0, V2, and V3 have the cattle relationship.
cattle(V0, V2, V3) :- -placental(V0, V2, V3), person(V0), person(V2), person(V3).

% Rule: r_05f26733e7c2  |  line_index: 9  |  NL: If it is true that V0 and V3 have the marmot relationship, and it is explicitly false that V2 and V4 have the squirrel relationship, and there is no evidence that it is true that V3 and V4 have the abrocome relationship, then it is true that V0, V3, and V4 have the rodent relationship.
rodent(V0, V3, V4) :- marmot(V0, V3), -squirrel(V2, V4), not abrocome(V3, V4), person(V0), person(V2), person(V3), person(V4).

% Rule: r_f7e91c81fdaa  |  line_index: 10  |  NL: If it is explicitly false that V0 and V2 have the yellowbelly marmot relationship, and it is true that V2 and V3 have the hoary marmot relationship, and it is explicitly false that V0, V1, and V2 have the sight organ relationship, then it is true that V0 and V3 have the marmot relationship.
marmot(V0, V3) :- -yellowbelly_marmot(V0, V2), hoary_marmot(V2, V3), -sight_organ(V0, V1, V2), person(V0), person(V1), person(V2), person(V3).

% Rule: r_07f797a3350c  |  line_index: 11  |  NL: If it is explicitly false that V0, V1, and V3 have the bovine relationship, and it is explicitly false that V0, V2, and V4 have the horn relationship, and there is no evidence that it is explicitly false that V0, V3, and V4 have the bullock relationship, then it is explicitly false that V0, V1, and V2 have the bull relationship.
-bull(V0, V1, V2) :- -bovine(V0, V1, V3), -horn(V0, V2, V4), not -bullock(V0, V3, V4), person(V0), person(V1), person(V2), person(V3), person(V4).

% Rule: r_9799ef84dea7  |  line_index: 12  |  NL: If it is explicitly false that V0, V1, and V3 have the bovine relationship, and it is explicitly false that V0, V2, and V4 have the horn relationship, and there is no evidence that it is explicitly false that V0, V3, and V4 have the bullock relationship, then it is explicitly false that V0, V3, and V4 have the udder relationship.
-udder(V0, V3, V4) :- -bovine(V0, V1, V3), -horn(V0, V2, V4), not -bullock(V0, V3, V4), person(V0), person(V1), person(V2), person(V3), person(V4).

% Rule: r_5c1889030e6c  |  line_index: 13  |  NL: If it is true that V0, V3, and V4 have the rodent relationship, and it is explicitly false that V0, V1, and V2 have the bull relationship, and there is no evidence that it is true that V0, V1, and V2 have the cow relationship, then it is explicitly false that V0, V2, and V3 have the placental relationship.
-placental(V0, V2, V3) :- rodent(V0, V3, V4), -bull(V0, V1, V2), not cow(V0, V1, V2), person(V0), person(V1), person(V2), person(V3), person(V4).

% Rule: r_0c01b5e88200  |  line_index: 14  |  NL: If it is true that V0, V3, and V4 have the rodent relationship, and there is no evidence that it is true that V0, V3, and V4 have the udder relationship, then it is explicitly false that V0, V0, and V4 have the cow relationship.
-cow(V0, V0, V4) :- rodent(V0, V3, V4), not udder(V0, V3, V4), person(V0), person(V3), person(V4).