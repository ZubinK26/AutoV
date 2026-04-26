% Bundle: symtex_batch_20260423_180417Z_2f5d90e2

person(aaron).
person(kimberly).
person(richard).
person(daniel).

% Rule: r_1b7548ba264b  |  line_index: 0  |  NL: The fact that Aaron is a chick of Kimberly is explicitly false.
-chick(aaron, kimberly).

% Rule: r_cfc617011660  |  line_index: 1  |  NL: The fact that Richard is an exodus of Aaron is explicitly false.
-exodus(richard, aaron).

% Rule: r_23e9892e435c  |  line_index: 2  |  NL: The fact that Richard is a mist of Kimberly is explicitly false.
-mist(richard, kimberly).

% Rule: r_cb97d4676d3c  |  line_index: 3  |  NL: The fact that Kimberly is playing harp with Daniel is explicitly false.
-playing_harp(kimberly, daniel).

% Rule: r_5f77c6ce2122  |  line_index: 4  |  NL: The fact that Aaron is a protection of Kimberly is explicitly false.
-protection(aaron, kimberly).

% Rule: r_0c2105289da8  |  line_index: 5  |  NL: The fact that Kimberly is a riding boot of Daniel is explicitly false.
-riding_boot(kimberly, daniel).

% Rule: r_e4c85a3a90c6  |  line_index: 6  |  NL: The fact that Kimberly is a room of Daniel is explicitly false.
-room(kimberly, daniel).

% Rule: r_54c9a6835e51  |  line_index: 7  |  NL: The fact that Richard is a summer of Daniel is explicitly false.
-summer(richard, daniel).

% Rule: r_253d9b9dd8b0  |  line_index: 8  |  NL: The fact that Richard is a bakery of Aaron is true.
bakery(richard, aaron).

% Rule: r_ceeb5bc63efb  |  line_index: 9  |  NL: The fact that Daniel is cold is true.
cold(daniel).

% Rule: r_ce6d3f683a1e  |  line_index: 10  |  NL: The fact that Richard is a creation of Aaron is true.
creation(richard, aaron).

% Rule: r_2b63138dd621  |  line_index: 11  |  NL: The fact that Aaron is a drop of Kimberly is true.
drop(aaron, kimberly).

% Rule: r_45d47bc9dbff  |  line_index: 12  |  NL: The fact that Richard is a garment cutter of Aaron is true.
garment_cutter(richard, aaron).

% Rule: r_b9675c223a8b  |  line_index: 13  |  NL: The fact that Daniel is heat is true.
heat(daniel).

% Rule: r_a85058e03cd6  |  line_index: 14  |  NL: The fact that Kimberly is a procedure of Daniel is true.
procedure(kimberly, daniel).

% Rule: r_5fe0af14408b  |  line_index: 15  |  NL: The fact that Aaron is a soup of Daniel is true.
soup(aaron, daniel).

% Rule: r_0bbb7befdc89  |  line_index: 16  |  NL: The fact that Daniel is steam is true.
steam(daniel).

% Rule: r_071429b2e405  |  line_index: 17  |  NL: If V0 is a summer of V3 is explicitly false and V1 is a chick of V2 is explicitly false and there is no evidence that V1 is a soup of V3 is explicitly false, then the fact that V1 is after is explicitly false.
-after(V1) :- -summer(V0, V3), -chick(V1, V2), not -soup(V1, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_ef194671f890  |  line_index: 18  |  NL: If V1 is a thunder of V2 is true and V1 is a zebu of V3 is true and there is no evidence that V2 is playing harp with V3 is true, then the fact that V1 is angels is explicitly false.
-angels(V1) :- thunder(V1, V2), zebu(V1, V3), not playing_harp(V2, V3), person(V1), person(V2), person(V3).

% Rule: r_453e0ae697e7  |  line_index: 19  |  NL: If V0 is a mist of V2 is explicitly false and V1 is a drop of V2 is true and V2 is a room of V3 is explicitly false, then the fact that V0 is a dew of V1 is explicitly false.
-dew(V0, V1) :- -mist(V0, V2), drop(V1, V2), -room(V2, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_a049021ce454  |  line_index: 20  |  NL: If V0 is a dew of V1 is true and V1 is a smoke of V3 is explicitly false and V1 is angels is true, then the fact that V1 is a drop of V0 is explicitly false.
-drop(V1, V0) :- dew(V0, V1), -smoke(V1, V3), angels(V1), person(V0), person(V1), person(V3).

% Rule: r_411fe4dc777e  |  line_index: 21  |  NL: If V3 is hot is true and V1 is after is true and there is no evidence that V1 is angels is explicitly false, then the fact that V1 is a drop of V3 is explicitly false.
-drop(V1, V3) :- hot(V3), after(V1), not -angels(V1), person(V1), person(V3).

% Rule: r_f6ad4e75f452  |  line_index: 22  |  NL: If V0 is a summer of V3 is explicitly false and V1 is a chick of V2 is explicitly false and there is no evidence that V1 is a soup of V3 is explicitly false, then the fact that V3 is hot is explicitly false.
-hot(V3) :- -summer(V0, V3), -chick(V1, V2), not -soup(V1, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_aaf74cdd0a31  |  line_index: 23  |  NL: If V0 is a dew of V1 is true and there is no evidence that V0 is a bakery of V1 is explicitly false, then the fact that V1 is a morning of V1 is explicitly false.
-morning(V1, V1) :- dew(V0, V1), not -bakery(V0, V1), person(V0), person(V1).

% Rule: r_f556a1a1089f  |  line_index: 24  |  NL: If V3 is hot is explicitly false and there is no evidence that V3 is heat is explicitly false and there is no evidence that V3 is cold is explicitly false, then the fact that V3 is a temperature of V3 is explicitly false.
-temperature(V3, V3) :- -hot(V3), not -heat(V3), not -cold(V3), person(V3).

% Rule: r_0f40999b62ed  |  line_index: 25  |  NL: If V3 is hot is true, then the fact that V3 is a thunder of V3 is explicitly false.
-thunder(V3, V3) :- hot(V3), person(V3).

% Rule: r_7e348147c43c  |  line_index: 26  |  NL: If V0 is a creation of V1 is true and V1 is a protection of V2 is explicitly false and V2 is a procedure of V3 is true, then V1 is an activity of V3 is true.
activity(V1, V3) :- creation(V0, V1), -protection(V1, V2), procedure(V2, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_eede64981612  |  line_index: 27  |  NL: If V1 is a thunder of V2 is explicitly false and V0 is a temperature of V3 is true and V1 is a morning of V3 is explicitly false, then V1 is after is true.
after(V1) :- -thunder(V1, V2), temperature(V0, V3), -morning(V1, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_914f2da4d5c2  |  line_index: 28  |  NL: If V1 is a fire of V3 is explicitly false and there is no evidence that V3 is hot is explicitly false and V0 is a temperature of V3 is true, then V1 is angels is true.
angels(V1) :- -fire(V1, V3), not -hot(V3), temperature(V0, V3), person(V0), person(V1), person(V3).

% Rule: r_dea0ba5f9499  |  line_index: 29  |  NL: If V3 is hot is true, then V3 is angels is true.
angels(V3) :- hot(V3), person(V3).

% Rule: r_4864f7226fd0  |  line_index: 30  |  NL: If V2 is a riding boot of V3 is explicitly false, then V2 is a boot of V3 is true.
boot(V2, V3) :- -riding_boot(V2, V3), person(V2), person(V3).

% Rule: r_779c6cd1d024  |  line_index: 31  |  NL: If V0 is an exodus of V1 is explicitly false, then V0 is an escape of V1 is true.
escape(V0, V1) :- -exodus(V0, V1), person(V0), person(V1).

% Rule: r_78721a70e4ea  |  line_index: 32  |  NL: If V3 is hot is explicitly false and V0 is a temperature of V3 is explicitly false and V1 is a smoke of V3 is true, then V1 is a fire of V3 is true.
fire(V1, V3) :- -hot(V3), -temperature(V0, V3), smoke(V1, V3), person(V0), person(V1), person(V3).

% Rule: r_e57eb463e60d  |  line_index: 33  |  NL: If V1 is a fire of V3 is explicitly false and V1 is after is true and V0 is a temperature of V3 is true, then V3 is hot is true.
hot(V3) :- -fire(V1, V3), after(V1), temperature(V0, V3), person(V0), person(V1), person(V3).

% Rule: r_7f808e9dce3d  |  line_index: 34  |  NL: If V0 is a dew of V1 is explicitly false and there is no evidence that V1 is after is true and there is no evidence that V0 is a garment cutter of V1 is explicitly false, then V1 is a morning of V1 is true.
morning(V1, V1) :- -dew(V0, V1), not after(V1), not -garment_cutter(V0, V1), person(V0), person(V1).

% Rule: r_593a0b6a6748  |  line_index: 35  |  NL: If V3 is hot is explicitly false and there is no evidence that V3 is steam is explicitly false, then V3 is a smoke of V3 is true.
smoke(V3, V3) :- -hot(V3), not -steam(V3), person(V3).

% Rule: r_9470e966b351  |  line_index: 36  |  NL: If V0 is a creation of V1 is true and V1 is a protection of V2 is explicitly false and V2 is a procedure of V3 is true, then V1 is a thunder of V2 is true.
thunder(V1, V2) :- creation(V0, V1), -protection(V1, V2), procedure(V2, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_1d1b2e3008e5  |  line_index: 37  |  NL: If V1 is an activity of V3 is true and there is no evidence that V1 is a fire of V3 is explicitly false and there is no evidence that V1 is a morning of V3 is explicitly false, then V1 is a zebu of V3 is true.
zebu(V1, V3) :- activity(V1, V3), not -fire(V1, V3), not -morning(V1, V3), person(V1), person(V3).