% Bundle: symtex_batch_20260423_180713Z_e28c4d4b

person(shelley).
person(rose).
person(tara).
person(cynthia).
person(V0) :- person(V0).
person(V1) :- person(V1).
person(V2) :- person(V2).
person(V3) :- person(V3).

% Rule: r_44a00e8c0075  |  line_index: 0  |  NL: Shelley is not born.
-born(shelley).

% Rule: r_c37e4467a21e  |  line_index: 1  |  NL: Rose is not crossing.
-crossing(rose).

% Rule: r_52f456787486  |  line_index: 2  |  NL: Rose does not die horribly with Tara.
-dies_horribly_with(rose, tara).

% Rule: r_437721874979  |  line_index: 3  |  NL: Cynthia does not have fur with Shelley.
-has_fur(cynthia, shelley).

% Rule: r_0dfee4d6add8  |  line_index: 4  |  NL: Modification is false.
-modification.

% Rule: r_257f5f1addab  |  line_index: 5  |  NL: Rose and Shelley do not have night time.
-has_night_time(rose, shelley).

% Rule: r_d7680fc9c3e7  |  line_index: 6  |  NL: Shelley is not an offerer.
-offerer(shelley).

% Rule: r_ea25df5324c9  |  line_index: 7  |  NL: Cynthia is not a thysanuran insect.
-thysanuran_insect(cynthia).

% Rule: r_ec40bfeeb1f7  |  line_index: 8  |  NL: Rose and Shelley have a double bed.
has_double_bed(rose, shelley).

% Rule: r_de07a6dc7cc5  |  line_index: 9  |  NL: Cynthia has a mailbox for Rose.
has_mailbox_for(cynthia, rose).

% Rule: r_f0a5ae89bea2  |  line_index: 10  |  NL: Cynthia moos at Rose.
moos_at(cynthia, rose).

% Rule: r_7ae47eea397d  |  line_index: 11  |  NL: Cynthia is traveling faster than Tara.
traveling_faster_than(cynthia, tara).

% Rule: r_29de02645517  |  line_index: 12  |  NL: Shelley has a trunk for Tara.
has_trunk_for(shelley, tara).

% Rule: r_0351c43a3e97  |  line_index: 13  |  NL: Rose is a tugboat for Shelley.
is_tugboat_for(rose, shelley).

% Rule: r_11770c6f269d  |  line_index: 14  |  NL: Rose has a work place with Shelley.
has_work_place_with(rose, shelley).

% Rule: r_ba5255956b2f  |  line_index: 15  |  NL: If V1 is not crossing, V0 has a mailbox for V1, V0 is traveling faster than V3, V1 and V2 do not have night time, and there is no evidence that V2 has a trunk for V3 being false, then V2 does not have body armor.
-has_body_armor(V2) :- -crossing(V1), has_mailbox_for(V0, V1), traveling_faster_than(V0, V3), -has_night_time(V1, V2), not -has_trunk_for(V2, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_aaac05965274  |  line_index: 16  |  NL: If V3 is a stepladder, V0 has a guinea worm with V1, and there is no evidence that modification is true, then V1 and V3 do not have a cliffhanger.
-has_cliffhanger(V1, V3) :- stepladder(V3), has_guinea_worm_with(V0, V1), not modification, person(V0), person(V1), person(V3).

% Rule: r_5101325c438e  |  line_index: 17  |  NL: If V1 and V2 do not have a cliffhanger, V2 has body armor, V0 has a guinea worm with V1, and V2 is not playing with friends, then V1 is not a course.
-course(V1) :- -has_cliffhanger(V1, V2), has_body_armor(V2), has_guinea_worm_with(V0, V1), -playing_with_friends(V2), person(V0), person(V1), person(V2).

% Rule: r_a7ecc006b5b4  |  line_index: 18  |  NL: If V3 is a stepladder, V0 has a guinea worm with V1, and V2 is not playing with friends, then V1 is not a course.
-course(V1) :- stepladder(V3), has_guinea_worm_with(V0, V1), -playing_with_friends(V2), person(V0), person(V1), person(V2), person(V3).

% Rule: r_3f95b588e2b5  |  line_index: 19  |  NL: If V1 and V2 have a cliffhanger, then V2 does not have a guinea worm with V1.
-has_guinea_worm_with(V2, V1) :- has_cliffhanger(V1, V2), person(V1), person(V2).

% Rule: r_414230dd67e8  |  line_index: 20  |  NL: If V1 and V2 have a sandwich shop, V3 is a stepladder, V1 and V2 do not have a palm, V1 and V2 do not have a nit, and there is no evidence that V1 has a breadbasket for V3, then V2 does not have a mailbox for V1.
-has_mailbox_for(V2, V1) :- has_sandwich_shop(V1, V2), stepladder(V3), -has_palm(V1, V2), -has_nit(V1, V2), not has_breadbasket_for(V1, V3), person(V1), person(V2), person(V3).

% Rule: r_694396453270  |  line_index: 21  |  NL: If V0 is not a thysanuran insect, V0 moos at V1, V1 has a work place with V2, V1 and V2 have a double bed, and V1 does not die horribly with V3, then V1 and V2 do not have a name puppy.
-has_name_puppy(V1, V2) :- -thysanuran_insect(V0), moos_at(V0, V1), has_work_place_with(V1, V2), has_double_bed(V1, V2), -dies_horribly_with(V1, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_87b6d03acb3c  |  line_index: 22  |  NL: If V1 is not a course, then V1 and V1 do not have a palm.
-has_palm(V1, V1) :- -course(V1), person(V1).

% Rule: r_7565d4790de4  |  line_index: 23  |  NL: If V1 is not crossing, V0 has a mailbox for V1, V0 is traveling faster than V3, V1 and V2 do not have night time, and there is no evidence that V2 has a trunk for V3 being false, then V1 and V2 do not have a sandwich shop.
-has_sandwich_shop(V1, V2) :- -crossing(V1), has_mailbox_for(V0, V1), traveling_faster_than(V0, V3), -has_night_time(V1, V2), not -has_trunk_for(V2, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_99cfa46d6490  |  line_index: 24  |  NL: If V0 and V2 do not have fur and V1 is a tugboat for V2, then V0 and V1 do not have a shetland pony.
-has_shetland_pony(V0, V1) :- -has_fur(V0, V2), is_tugboat_for(V1, V2), person(V0), person(V1), person(V2).

% Rule: r_8df186828e19  |  line_index: 25  |  NL: If V1 and V2 do not have a sandwich shop, there is no evidence that V1 and V2 do not have a palm, and there is no evidence that V1 and V2 do not have a nit, then V1 is not a stepladder.
-stepladder(V1) :- -has_sandwich_shop(V1, V2), not -has_palm(V1, V2), not -has_nit(V1, V2), person(V1), person(V2).

% Rule: r_e53fb0fba229  |  line_index: 26  |  NL: If V2 has body armor, V2 is not born, and V2 is not an offerer, then V2 is not traveling faster than V2.
-traveling_faster_than(V2, V2) :- has_body_armor(V2), -born(V2), -offerer(V2), person(V2).

% Rule: r_386468418561  |  line_index: 27  |  NL: If there is no evidence that V1 and V2 have a cliffhanger, V3 is a stepladder, and V1 and V2 do not have a nit, then V2 has body armor.
has_body_armor(V2) :- not has_cliffhanger(V1, V2), stepladder(V3), -has_nit(V1, V2), person(V1), person(V2), person(V3).

% Rule: r_13e855028d95  |  line_index: 28  |  NL: If V2 does not have body armor and there is no evidence that V2 is not playing with friends, then V2 has a breadbasket for V2.
has_breadbasket_for(V2, V2) :- -has_body_armor(V2), not -playing_with_friends(V2), person(V2).

% Rule: r_96f75be7abb6  |  line_index: 29  |  NL: If V1 is not crossing, V0 has a mailbox for V1, V0 is traveling faster than V3, V1 and V2 do not have night time, and there is no evidence that V2 has a trunk for V3 being false, then V1 and V2 have a cliffhanger.
has_cliffhanger(V1, V2) :- -crossing(V1), has_mailbox_for(V0, V1), traveling_faster_than(V0, V3), -has_night_time(V1, V2), not -has_trunk_for(V2, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_085c05e8b2a6  |  line_index: 30  |  NL: If V3 is not a stepladder, V0 does not have a guinea worm with V1, and there is no evidence that V1 has a breadbasket for V3 being false, then V1 is a course.
course(V1) :- -stepladder(V3), -has_guinea_worm_with(V0, V1), not -has_breadbasket_for(V1, V3), person(V0), person(V1), person(V3).

% Rule: r_287a09cffd32  |  line_index: 31  |  NL: If V1 and V2 have a sandwich shop, V1 and V2 do not have a cliffhanger, V2 has body armor, V1 has a breadbasket for V3 being false, and there is no evidence that V1 is a course, then V1 and V2 have night time.
has_night_time(V1, V2) :- has_sandwich_shop(V1, V2), -has_cliffhanger(V1, V2), has_body_armor(V2), -has_breadbasket_for(V1, V3), not course(V1), person(V1), person(V2), person(V3).

% Rule: r_dc7d19e3961f  |  line_index: 32  |  NL: If V1 and V2 have a palm, then V1 and V2 have a nit.
has_nit(V1, V2) :- has_palm(V1, V2), person(V1), person(V2).

% Rule: r_7b18d2ccc7d9  |  line_index: 33  |  NL: If V1 and V2 have a cliffhanger, then V1 and V2 have a palm.
has_palm(V1, V2) :- has_cliffhanger(V1, V2), person(V1), person(V2).

% Rule: r_56731570a3ef  |  line_index: 34  |  NL: If V1 and V2 have a cliffhanger, then V2 is playing with friends.
playing_with_friends(V2) :- has_cliffhanger(V1, V2), person(V1), person(V2).