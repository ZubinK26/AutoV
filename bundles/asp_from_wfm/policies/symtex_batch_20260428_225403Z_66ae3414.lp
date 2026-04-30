% Bundle: symtex_batch_20260428_225403Z_66ae3414

person(benjamin).
person(christina).
person(joy).
person(leonard).

% Rule: r_53dd21a7e06a  |  line_index: 0  |  NL: Christina is not an adult.
-adult(christina).

% Rule: r_8354e1fb7018  |  line_index: 1  |  NL: The relationship bass between Benjamin and Christina is explicitly false.
-bass(benjamin, christina).

% Rule: r_9cdc836bc26c  |  line_index: 2  |  NL: The relationship beryl between Joy and Leonard is explicitly false.
-beryl(joy, leonard).

% Rule: r_7bbf006a2ec6  |  line_index: 3  |  NL: The relationship bureaucratic procedure between Joy and Christina is explicitly false.
-bureaucratic_procedure(joy, christina).

% Rule: r_bd4eb88cf523  |  line_index: 4  |  NL: The relationship erectile tissue between Leonard and Christina is explicitly false.
-erectile_tissue(leonard, christina).

% Rule: r_c424a34e7136  |  line_index: 5  |  NL: Joy is not a Hong Kong dollar.
-hong_kong_dollar(joy).

% Rule: r_d2711596390a  |  line_index: 6  |  NL: The relationship mother of pearl between Benjamin and Joy is explicitly false.
-mother_of_pearl(benjamin, joy).

% Rule: r_1803550b13b1  |  line_index: 7  |  NL: The relationship ninian between Leonard and Christina is explicitly false.
-ninian(leonard, christina).

% Rule: r_9aab42522274  |  line_index: 8  |  NL: Leonard is not an open sesame.
-open_sesame(leonard).

% Rule: r_dad01bf856f4  |  line_index: 9  |  NL: The relationship sawdust doll between Benjamin and Leonard is explicitly false.
-sawdust_doll(benjamin, leonard).

% Rule: r_ac3e7ce14f28  |  line_index: 10  |  NL: Christina is not a skin.
-skin(christina).

% Rule: r_144100e656b3  |  line_index: 11  |  NL: The relationship small print between Joy and Christina is explicitly false.
-small_print(joy, christina).

% Rule: r_de9a0687d5fe  |  line_index: 12  |  NL: The relationship smoke between Benjamin and Joy is explicitly false.
-smoke(benjamin, joy).

% Rule: r_46d0c5d2b477  |  line_index: 13  |  NL: The relationship utensil between Joy and Christina is explicitly false.
-utensil(joy, christina).

% Rule: r_f847ab9b2a93  |  line_index: 14  |  NL: The relationship carbonado between Benjamin and Joy is true.
carbonado(benjamin, joy).

% Rule: r_2aa7d7b29a26  |  line_index: 15  |  NL: The relationship coloring between Benjamin and Joy is true.
coloring(benjamin, joy).

% Rule: r_bb88533c3274  |  line_index: 16  |  NL: The relationship dimension between Leonard and Christina is true.
dimension(leonard, christina).

% Rule: r_eabcaec6c179  |  line_index: 17  |  NL: The relationship heating element between Benjamin and Joy is true.
heating_element(benjamin, joy).

% Rule: r_4ea576778dbc  |  line_index: 18  |  NL: Benjamin kills Joy.
kills(benjamin, joy).

% Rule: r_77d6c9c8fa42  |  line_index: 19  |  NL: The relationship race between Joy and Christina is true.
race(joy, christina).

% Rule: r_a4009daab7a8  |  line_index: 20  |  NL: Benjamin sings songs to Joy.
sings_songs(benjamin, joy).

% Rule: r_daa94b500cce  |  line_index: 21  |  NL: If V0 connects to hallways V1, then acculturation of V1 is explicitly false.
-acculturation(V1) :- connects_to_hallways(V0, V1).

% Rule: r_e7c311aef8a7  |  line_index: 22  |  NL: If V1 is a drinking establishment for V3 and V0 connects to hallways V1 and V2 is not holding V3, then acculturation of V1 is explicitly false.
-acculturation(V1) :- drinking_establishment(V1, V3), connects_to_hallways(V0, V1), -holding(V2, V3).

% Rule: r_271b34c34ad3  |  line_index: 23  |  NL: If V0 does not connect to hallways V1 and the relationship mother of pearl between V0 and V1 is not true and V0 does not smoke with V1, then the coinage of V1 for V0 is explicitly false.
-coinage(V1, V0) :- -connects_to_hallways(V0, V1), not mother_of_pearl(V0, V1), -smoke(V0, V1), person(V0), person(V1).

% Rule: r_fd7165c7e5c4  |  line_index: 24  |  NL: If V1 is not a Hong Kong dollar and the relationship sawdust doll between V0 and V2 is explicitly false and the relationship beryl between V1 and V2 is explicitly false and the relationship erectile tissue between V2 and V3 is explicitly false and the relationship ninian between V2 and V3 is explicitly false, then the fishing trip of V1 is explicitly false.
-fishing_trip(V1) :- -hong_kong_dollar(V1), -sawdust_doll(V0, V2), -beryl(V1, V2), -erectile_tissue(V2, V3), -ninian(V2, V3).

% Rule: r_94e55c9373a8  |  line_index: 25  |  NL: If the hand luggage relationship between V1 and V2 is explicitly false, then the solleret of V1 is explicitly false.
-solleret(V1) :- -hand_luggage(V1, V2).

% Rule: r_e0615274db1f  |  line_index: 26  |  NL: If the hand luggage relationship between V1 and V2 is true and V1 is a warner for V3 and there is no evidence that V2 is not holding V3, then the acculturation of V1 is true.
acculturation(V1) :- hand_luggage(V1, V2), warner(V1, V3), not -holding(V2, V3).

% Rule: r_a3b2500fbced  |  line_index: 27  |  NL: If V3 is not an adult and Benjamin kills Joy and there is no evidence that the relationship bass between V0 and V3 is true, then the cinnamon bread of V1 is true.
cinnamon_bread(V1) :- -adult(V3), kills(benjamin, joy), not bass(V0, V3), person(V1), person(V0).

% Rule: r_fccb248cbe1e  |  line_index: 28  |  NL: If there is no evidence that V1 is a warner for V3 and there is no evidence that the relationship central America exists between V1 and V3 and the relationship bureaucratic procedure between V1 and V3 is explicitly false, then V3 connects to hallways V1.
connects_to_hallways(V3, V1) :- not warner(V1, V3), not central_america(V1, V3), -bureaucratic_procedure(V1, V3), person(V1), person(V3).

% Rule: r_fb76a0348c15  |  line_index: 29  |  NL: If V2 is not an open sesame and V3 is not a skin and the relationship coloring between V0 and V1 is true and there is no evidence that the relationship race between V1 and V3 is explicitly false and there is no evidence that the relationship dimension between V2 and V3 is explicitly false, then the hand luggage relationship between V1 and V2 is true or V1 is not a drinking establishment for V3 or the solleret of V3 is true or V0 does not connect to hallways V1.
hand_luggage(V1, V2) | -drinking_establishment(V1, V3) | solleret(V3) | -connects_to_hallways(V0, V1) :- -open_sesame(V2), -skin(V3), coloring(V0, V1), not -race(V1, V3), not -dimension(V2, V3).

% Rule: r_8c6e84733502  |  line_index: 30  |  NL: If the solleret of V3 is true, then V3 is holding V3 or the relationship central America exists between V3 and V3.
holding(V3, V3) | central_america(V3, V3) :- solleret(V3).

% Rule: r_288332fe109b  |  line_index: 31  |  NL: If there is no evidence that V0 does not connect to hallways V1 and the relationship warner between V1 and V3 is explicitly false and there is no evidence that the relationship heating element between V0 and V1 is explicitly false and Benjamin sings songs to Joy and the relationship carbonado between V0 and V1 is true, then the relationship mother of pearl between V0 and V1 is true.
mother_of_pearl(V0, V1) :- not -connects_to_hallways(V0, V1), -warner(V1, V3), not -heating_element(V0, V1), sings_songs(benjamin, joy), carbonado(V0, V1), person(V3).

% Rule: r_74a3d4e40303  |  line_index: 32  |  NL: If V0 connects to hallways V1, then V0 is an open sesame.
open_sesame(V0) :- connects_to_hallways(V0, V1).

% Rule: r_927b05fa351a  |  line_index: 33  |  NL: If the acculturation of V1 is explicitly false, then V1 is an open sesame.
open_sesame(V1) :- -acculturation(V1).

% Rule: r_f36d59aafd7b  |  line_index: 34  |  NL: If V2 is not holding V3 and there is no evidence that the relationship central America exists between V1 and V3 and the acculturation of V1 is explicitly false, then V2 is an open sesame.
open_sesame(V2) :- -holding(V2, V3), not central_america(V1, V3), -acculturation(V1), person(V1).

% Rule: r_9d01b48ae934  |  line_index: 35  |  NL: If V1 is not a drinking establishment for V3 and there is no evidence that the relationship central America between V1 and V3 is explicitly false and there is no evidence that the relationship coinage between V1 and V3 is true and there is no evidence that the relationship small print between V1 and V3 is true and there is no evidence that the relationship utensil between V1 and V3 is true, then V1 is a warner for V3.
warner(V1, V3) :- -drinking_establishment(V1, V3), not -central_america(V1, V3), not coinage(V1, V3), not small_print(V1, V3), not utensil(V1, V3), person(V1), person(V3).