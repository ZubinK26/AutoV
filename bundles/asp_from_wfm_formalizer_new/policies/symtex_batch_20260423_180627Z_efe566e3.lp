% Bundle: symtex_batch_20260423_180627Z_efe566e3
% Rule: r_a2335be844d5  |  line_index: 0  |  NL: It is explicitly false that Mary and Sabrina have the yellowbelly marmot relationship.
-yellowbelly_marmot(mary, sabrina).
% Rule: r_f6b58fdb3a28  |  line_index: 1  |  NL: It is explicitly false that Mary, Alison, and Cynthia have the bovine relationship.
-bovine(mary, alison, cynthia).
% Rule: r_4dcd4927f6ce  |  line_index: 2  |  NL: It is explicitly false that Mary, Sabrina, and Anthony have the horn relationship.
-horn(mary, sabrina, anthony).
% Rule: r_2394d218b8ca  |  line_index: 3  |  NL: It is true that Mary, Cynthia, and Anthony have the bullock relationship.
bullock(mary, cynthia, anthony).
% Rule: r_67686167b73e  |  line_index: 4  |  NL: It is true that Sabrina and Cynthia have the hoary marmot relationship.
hoary_marmot(sabrina, cynthia).
% Rule: r_8bbd25b4ecb8  |  line_index: 5  |  NL: It is explicitly false that Mary, Alison, and Sabrina have the sight organ relationship.
-sight_organ(mary, alison, sabrina).
% Rule: r_8ee8a46abfaf  |  line_index: 6  |  NL: It is explicitly false that Sabrina and Anthony have the squirrel relationship.
-squirrel(sabrina, anthony).
% Rule: r_4b0531d7073f  |  line_index: 7  |  NL: It is explicitly false that Cynthia and Anthony have the abrocome relationship.
-abrocome(cynthia, anthony).
% Rule: r_6a80a876948e  |  line_index: 8  |  NL: If it is explicitly false that V0, V2, and V3 have the placental relationship, then it is true that V0, V2, and V3 have the cattle relationship.
cattle(V0, V2, V3) :- -placental(V0, V2, V3).
% Rule: r_fbc30c9cf607  |  line_index: 9  |  NL: If it is true that V0 and V3 have the marmot relationship, and it is explicitly false that V2 and V4 have the squirrel relationship, and there is no evidence that it is true that V3 and V4 have the abrocome relationship, then it is true that V0, V3, and V4 have the rodent relationship.
rodent(V0, V3, V4) :- marmot(V0, V3), -squirrel(V2, V4), not abrocome(V3, V4).
% Rule: r_1abc1c65441a  |  line_index: 10  |  NL: If it is explicitly false that V0 and V2 have the yellowbelly marmot relationship, and it is true that V2 and V3 have the hoary marmot relationship, and it is explicitly false that V0, V1, and V2 have the sight organ relationship, then it is true that V0 and V3 have the marmot relationship.
marmot(V0, V3) :- -yellowbelly_marmot(V0, V2), hoary_marmot(V2, V3), -sight_organ(V0, V1, V2).
% Rule: r_ff89c9be2dce  |  line_index: 11  |  NL: If it is explicitly false that V0, V1, and V3 have the bovine relationship, and it is explicitly false that V0, V2, and V4 have the horn relationship, and there is no evidence that it is explicitly false that V0, V3, and V4 have the bullock relationship, then it is explicitly false that V0, V1, and V2 have the bull relationship.
-bull(V0, V1, V2) :- -bovine(V0, V1, V3), -horn(V0, V2, V4), not -bullock(V0, V3, V4).
% Rule: r_cab6479e6d4a  |  line_index: 12  |  NL: If it is explicitly false that V0, V1, and V3 have the bovine relationship, and it is explicitly false that V0, V2, and V4 have the horn relationship, and there is no evidence that it is explicitly false that V0, V3, and V4 have the bullock relationship, then it is explicitly false that V0, V3, and V4 have the udder relationship.
-udder(V0, V3, V4) :- -bovine(V0, V1, V3), -horn(V0, V2, V4), not -bullock(V0, V3, V4).
% Rule: r_a3e934318627  |  line_index: 13  |  NL: If it is true that V0, V3, and V4 have the rodent relationship, and it is explicitly false that V0, V1, and V2 have the bull relationship, and there is no evidence that it is true that V0, V1, and V2 have the cow relationship, then it is explicitly false that V0, V2, and V3 have the placental relationship.
-placental(V0, V2, V3) :- rodent(V0, V3, V4), -bull(V0, V1, V2), not cow(V0, V1, V2).
% Rule: r_c6b7a8d3bca0  |  line_index: 14  |  NL: If it is true that V0, V3, and V4 have the rodent relationship, and there is no evidence that it is true that V0, V3, and V4 have the udder relationship, then it is explicitly false that V0, V0, and V4 have the cow relationship.
-cow(V0, V0, V4) :- rodent(V0, V3, V4), not udder(V0, V3, V4).