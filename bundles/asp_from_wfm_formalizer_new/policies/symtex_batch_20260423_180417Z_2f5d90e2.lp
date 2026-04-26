% Bundle: symtex_batch_20260423_180417Z_2f5d90e2
% Rule: r_e2546f5f9153  |  line_index: 0  |  NL: The fact that Aaron is a chick of Kimberly is explicitly false.
-chick(aaron, kimberly).
% Rule: r_cd1f35454574  |  line_index: 1  |  NL: The fact that Richard is an exodus of Aaron is explicitly false.
-exodus(richard, aaron).
% Rule: r_0cf7000afc77  |  line_index: 2  |  NL: The fact that Richard is a mist of Kimberly is explicitly false.
-mist(richard, kimberly).
% Rule: r_1d26d80e5360  |  line_index: 3  |  NL: The fact that Kimberly is playing harp with Daniel is explicitly false.
-playing_harp(kimberly, daniel).
% Rule: r_7243751b7031  |  line_index: 4  |  NL: The fact that Aaron is a protection of Kimberly is explicitly false.
-protection(aaron, kimberly).
% Rule: r_51a9fb9d1695  |  line_index: 5  |  NL: The fact that Kimberly is a riding boot of Daniel is explicitly false.
-riding_boot(kimberly, daniel).
% Rule: r_1a3744546755  |  line_index: 6  |  NL: The fact that Kimberly is a room of Daniel is explicitly false.
-room(kimberly, daniel).
% Rule: r_789a06cf9250  |  line_index: 7  |  NL: The fact that Richard is a summer of Daniel is explicitly false.
-summer(richard, daniel).
% Rule: r_dd9aefc0fc23  |  line_index: 8  |  NL: The fact that Richard is a bakery of Aaron is true.
bakery(richard, aaron).
% Rule: r_f403bda72742  |  line_index: 9  |  NL: The fact that Daniel is cold is true.
cold(daniel).
% Rule: r_2d753a0b288c  |  line_index: 10  |  NL: The fact that Richard is a creation of Aaron is true.
creation(richard, aaron).
% Rule: r_419a20233a13  |  line_index: 11  |  NL: The fact that Aaron is a drop of Kimberly is true.
drop(aaron, kimberly).
% Rule: r_2ad6d21bd292  |  line_index: 12  |  NL: The fact that Richard is a garment cutter of Aaron is true.
garment_cutter(richard, aaron).
% Rule: r_8c6d34966bea  |  line_index: 13  |  NL: The fact that Daniel is heat is true.
heat(daniel).
% Rule: r_d44881be742c  |  line_index: 14  |  NL: The fact that Kimberly is a procedure of Daniel is true.
procedure(kimberly, daniel).
% Rule: r_d367db0c8eb3  |  line_index: 15  |  NL: The fact that Aaron is a soup of Daniel is true.
soup(aaron, daniel).
% Rule: r_7c323bbae9fd  |  line_index: 16  |  NL: The fact that Daniel is steam is true.
steam(daniel).
% Rule: r_2be51012f81f  |  line_index: 17  |  NL: If V0 is a summer of V3 is explicitly false and V1 is a chick of V2 is explicitly false and there is no evidence that V1 is a soup of V3 is explicitly false, then the fact that V1 is after is explicitly false.
-after(V1) :- -summer(V0, V3), -chick(V1, V2), not -soup(V1, V3).
% Rule: r_7df26c6196c0  |  line_index: 18  |  NL: If V1 is a thunder of V2 is true and V1 is a zebu of V3 is true and there is no evidence that V2 is playing harp with V3 is true, then the fact that V1 is angels is explicitly false.
-angels(V1) :- thunder(V1, V2), zebu(V1, V3), not playing_harp(V2, V3).
% Rule: r_9f6a4e792712  |  line_index: 19  |  NL: If V0 is a mist of V2 is explicitly false and V1 is a drop of V2 is true and V2 is a room of V3 is explicitly false, then the fact that V0 is a dew of V1 is explicitly false.
-dew(V0, V1) :- -mist(V0, V2), drop(V1, V2), -room(V2, V3).
% Rule: r_f6043f3f8c5d  |  line_index: 20  |  NL: If V0 is a dew of V1 is true and V1 is a smoke of V3 is explicitly false and V1 is angels is true, then the fact that V1 is a drop of V0 is explicitly false.
-drop(V1, V0) :- dew(V0, V1), -smoke(V1, V3), angels(V1).
% Rule: r_704d991ba149  |  line_index: 21  |  NL: If V3 is hot is true and V1 is after is true and there is no evidence that V1 is angels is explicitly false, then the fact that V1 is a drop of V3 is explicitly false.
-drop(V1, V3) :- hot(V3), after(V1), not -angels(V1).
% Rule: r_3122ae1f07e7  |  line_index: 22  |  NL: If V0 is a summer of V3 is explicitly false and V1 is a chick of V2 is explicitly false and there is no evidence that V1 is a soup of V3 is explicitly false, then the fact that V3 is hot is explicitly false.
-hot(V3) :- -summer(V0, V3), -chick(V1, V2), not -soup(V1, V3).
% Rule: r_f2741f53253d  |  line_index: 23  |  NL: If V0 is a dew of V1 is true and there is no evidence that V0 is a bakery of V1 is explicitly false, then the fact that V1 is a morning of V1 is explicitly false.
-morning(V1, V1) :- dew(V0, V1), not -bakery(V0, V1).
% Rule: r_b05776c9b156  |  line_index: 24  |  NL: If V3 is hot is explicitly false and there is no evidence that V3 is heat is explicitly false and there is no evidence that V3 is cold is explicitly false, then the fact that V3 is a temperature of V3 is explicitly false.
-temperature(V3, V3) :- -hot(V3), not -heat(V3), not -cold(V3).
% Rule: r_879a1e67d511  |  line_index: 25  |  NL: If V3 is hot is true, then the fact that V3 is a thunder of V3 is explicitly false.
-thunder(V3, V3) :- hot(V3).
% Rule: r_2ed338dbed82  |  line_index: 26  |  NL: If V0 is a creation of V1 is true and V1 is a protection of V2 is explicitly false and V2 is a procedure of V3 is true, then V1 is an activity of V3 is true.
activity(V1, V3) :- creation(V0, V1), -protection(V1, V2), procedure(V2, V3).
% Rule: r_395757a855a7  |  line_index: 27  |  NL: If V1 is a thunder of V2 is explicitly false and V0 is a temperature of V3 is true and V1 is a morning of V3 is explicitly false, then V1 is after is true.
after(V1) :- -thunder(V1, V2), temperature(V0, V3), -morning(V1, V3).
% Rule: r_8333e30dbb09  |  line_index: 28  |  NL: If V1 is a fire of V3 is explicitly false and there is no evidence that V3 is hot is explicitly false and V0 is a temperature of V3 is true, then V1 is angels is true.
angels(V1) :- -fire(V1, V3), not -hot(V3), temperature(V0, V3).
% Rule: r_c19ce2284206  |  line_index: 29  |  NL: If V3 is hot is true, then V3 is angels is true.
angels(V3) :- hot(V3).
% Rule: r_205ccc3c0c31  |  line_index: 30  |  NL: If V2 is a riding boot of V3 is explicitly false, then V2 is a boot of V3 is true.
boot(V2, V3) :- -riding_boot(V2, V3).
% Rule: r_770e2c4da31f  |  line_index: 31  |  NL: If V0 is an exodus of V1 is explicitly false, then V0 is an escape of V1 is true.
escape(V0, V1) :- -exodus(V0, V1).
% Rule: r_c839d572e79b  |  line_index: 32  |  NL: If V3 is hot is explicitly false and V0 is a temperature of V3 is explicitly false and V1 is a smoke of V3 is true, then V1 is a fire of V3 is true.
fire(V1, V3) :- -hot(V3), -temperature(V0, V3), smoke(V1, V3).
% Rule: r_abfadf3783fb  |  line_index: 33  |  NL: If V1 is a fire of V3 is explicitly false and V1 is after is true and V0 is a temperature of V3 is true, then V3 is hot is true.
hot(V3) :- -fire(V1, V3), after(V1), temperature(V0, V3).
% Rule: r_9159757e24bf  |  line_index: 34  |  NL: If V0 is a dew of V1 is explicitly false and there is no evidence that V1 is after is true and there is no evidence that V0 is a garment cutter of V1 is explicitly false, then V1 is a morning of V1 is true.
morning(V1, V1) :- -dew(V0, V1), not after(V1), not -garment_cutter(V0, V1).
% Rule: r_dadda5e2560c  |  line_index: 35  |  NL: If V3 is hot is explicitly false and there is no evidence that V3 is steam is explicitly false, then V3 is a smoke of V3 is true.
smoke(V3, V3) :- -hot(V3), not -steam(V3).
% Rule: r_5de9fcd1b0b3  |  line_index: 36  |  NL: If V0 is a creation of V1 is true and V1 is a protection of V2 is explicitly false and V2 is a procedure of V3 is true, then V1 is a thunder of V2 is true.
thunder(V1, V2) :- creation(V0, V1), -protection(V1, V2), procedure(V2, V3).
% Rule: r_e066b522c5c5  |  line_index: 37  |  NL: If V1 is an activity of V3 is true and there is no evidence that V1 is a fire of V3 is explicitly false and there is no evidence that V1 is a morning of V3 is explicitly false, then V1 is a zebu of V3 is true.
zebu(V1, V3) :- activity(V1, V3), not -fire(V1, V3), not -morning(V1, V3).