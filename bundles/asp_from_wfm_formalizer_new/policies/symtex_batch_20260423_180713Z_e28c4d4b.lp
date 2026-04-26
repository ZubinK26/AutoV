% Bundle: symtex_batch_20260423_180713Z_e28c4d4b

% Rule: r_711809d5c28f  |  line_index: 0  |  NL: Shelley is not born.
-born(shelley).

% Rule: r_42372fbafe31  |  line_index: 1  |  NL: Rose is not crossing.
-crossing(rose).

% Rule: r_3c6fe20982d1  |  line_index: 2  |  NL: Rose does not die horribly with Tara.
-die_horribly(rose, tara).

% Rule: r_19c636087dd2  |  line_index: 3  |  NL: Cynthia does not have fur with Shelley.
-fur(cynthia, shelley).

% Rule: r_13b70d61ccd2  |  line_index: 4  |  NL: Modification is false.
-modification.

% Rule: r_99ebdcbdcc17  |  line_index: 5  |  NL: Rose and Shelley do not have night time.
-night_time(rose, shelley).

% Rule: r_5e70af3957eb  |  line_index: 6  |  NL: Shelley is not an offerer.
-offerer(shelley).

% Rule: r_b7a156907e12  |  line_index: 7  |  NL: Cynthia is not a thysanuran insect.
-thysanuran_insect(cynthia).

% Rule: r_52bc3fcbb87a  |  line_index: 8  |  NL: Rose and Shelley have a double bed.
double_bed(rose, shelley).

% Rule: r_08037ea82c9d  |  line_index: 9  |  NL: Cynthia has a mailbox for Rose.
mailbox(cynthia, rose).

% Rule: r_9e13efac2b50  |  line_index: 10  |  NL: Cynthia moos at Rose.
moos(cynthia, rose).

% Rule: r_69e45543f35e  |  line_index: 11  |  NL: Cynthia is traveling faster than Tara.
traveling_faster(cynthia, tara).

% Rule: r_4b4edfa60c23  |  line_index: 12  |  NL: Shelley has a trunk for Tara.
trunk(shelley, tara).

% Rule: r_0cd54f502816  |  line_index: 13  |  NL: Rose is a tugboat for Shelley.
tugboat(rose, shelley).

% Rule: r_5d55e4cbb4ab  |  line_index: 14  |  NL: Rose has a work place with Shelley.
work_place(rose, shelley).

% Rule: r_7f3840a2bb74  |  line_index: 15  |  NL: If V1 is not crossing, V0 has a mailbox for V1, V0 is traveling faster than V3, V1 and V2 do not have night time, and there is no evidence that V2 has a trunk for V3 being false, then V2 does not have body armor.
-body_armor(V2) :- -crossing(V1), mailbox(V0, V1), traveling_faster(V0, V3), -night_time(V1, V2), not -trunk(V2, V3).

% Rule: r_1cbc5b62ef68  |  line_index: 16  |  NL: If V3 is a stepladder, V0 has a guinea worm with V1, and there is no evidence that modification is true, then V1 and V3 do not have a cliffhanger.
-cliffhanger(V1, V3) :- stepladder(V3), guinea_worm(V0, V1), not modification.

% Rule: r_0423519e6c35  |  line_index: 17  |  NL: If V1 and V2 do not have a cliffhanger, V2 has body armor, V0 has a guinea worm with V1, and V2 is not playing with friends, then V1 is not a course.
-course(V1) :- -cliffhanger(V1, V2), body_armor(V2), guinea_worm(V0, V1), -playing_with_friends(V2).

% Rule: r_d051057d6d39  |  line_index: 18  |  NL: If V3 is a stepladder, V0 has a guinea worm with V1, and V2 is not playing with friends, then V1 is not a course.
-course(V1) :- stepladder(V3), guinea_worm(V0, V1), -playing_with_friends(V2).

% Rule: r_8028fb75c244  |  line_index: 19  |  NL: If V1 and V2 have a cliffhanger, then V2 does not have a guinea worm with V1.
-guinea_worm(V2, V1) :- cliffhanger(V1, V2).

% Rule: r_fc2cfff656e5  |  line_index: 20  |  NL: If V1 and V2 have a sandwich shop, V3 is a stepladder, V1 and V2 do not have a palm, V1 and V2 do not have a nit, and there is no evidence that V1 has a breadbasket for V3, then V2 does not have a mailbox for V1.
-mailbox(V2, V1) :- sandwich_shop(V1, V2), stepladder(V3), -palm(V1, V2), -nit(V1, V2), not breadbasket(V1, V3).

% Rule: r_be031b6586c6  |  line_index: 21  |  NL: If V0 is not a thysanuran insect, V0 moos at V1, V1 has a work place with V2, V1 and V2 have a double bed, and V1 does not die horribly with V3, then V1 and V2 do not have a name puppy.
-name_puppy(V1, V2) :- -thysanuran_insect(V0), moos(V0, V1), work_place(V1, V2), double_bed(V1, V2), -die_horribly(V1, V3).

% Rule: r_3aa1d4a8f4c9  |  line_index: 22  |  NL: If V1 is not a course, then V1 and V1 do not have a palm.
-palm(V1, V1) :- -course(V1).

% Rule: r_6244ad8826dc  |  line_index: 23  |  NL: If V1 is not crossing, V0 has a mailbox for V1, V0 is traveling faster than V3, V1 and V2 do not have night time, and there is no evidence that V2 has a trunk for V3 being false, then V1 and V2 do not have a sandwich shop.
-sandwich_shop(V1, V2) :- -crossing(V1), mailbox(V0, V1), traveling_faster(V0, V3), -night_time(V1, V2), not -trunk(V2, V3).

% Rule: r_5680586d1512  |  line_index: 24  |  NL: If V0 and V2 do not have fur and V1 is a tugboat for V2, then V0 and V1 do not have a shetland pony.
-shetland_pony(V0, V1) :- -fur(V0, V2), tugboat(V1, V2).

% Rule: r_43cb94ad0088  |  line_index: 25  |  NL: If V1 and V2 do not have a sandwich shop, there is no evidence that V1 and V2 do not have a palm, and there is no evidence that V1 and V2 do not have a nit, then V1 is not a stepladder.
-stepladder(V1) :- -sandwich_shop(V1, V2), not -palm(V1, V2), not -nit(V1, V2).

% Rule: r_5eb72b97cd7e  |  line_index: 26  |  NL: If V2 has body armor, V2 is not born, and V2 is not an offerer, then V2 is not traveling faster than V2.
-traveling_faster(V2, V2) :- body_armor(V2), -born(V2), -offerer(V2).

% Rule: r_8fdff055c420  |  line_index: 27  |  NL: If there is no evidence that V1 and V2 have a cliffhanger, V3 is a stepladder, and V1 and V2 do not have a nit, then V2 has body armor.
body_armor(V2) :- not cliffhanger(V1, V2), stepladder(V3), -nit(V1, V2).

% Rule: r_4d0200b50cbc  |  line_index: 28  |  NL: If V2 does not have body armor and there is no evidence that V2 is not playing with friends, then V2 has a breadbasket for V2.
breadbasket(V2, V2) :- -body_armor(V2), not -playing_with_friends(V2).

% Rule: r_1660f8c206f8  |  line_index: 29  |  NL: If V1 is not crossing, V0 has a mailbox for V1, V0 is traveling faster than V3, V1 and V2 do not have night time, and there is no evidence that V2 has a trunk for V3 being false, then V1 and V2 have a cliffhanger.
cliffhanger(V1, V2) :- -crossing(V1), mailbox(V0, V1), traveling_faster(V0, V3), -night_time(V1, V2), not -trunk(V2, V3).

% Rule: r_4a45835d485e  |  line_index: 30  |  NL: If V3 is not a stepladder, V0 does not have a guinea worm with V1, and there is no evidence that V1 has a breadbasket for V3 being false, then V1 is a course.
course(V1) :- -stepladder(V3), -guinea_worm(V0, V1), not -breadbasket(V1, V3).

% Rule: r_96d52cea1974  |  line_index: 31  |  NL: If V1 and V2 have a sandwich shop, V1 and V2 do not have a cliffhanger, V2 has body armor, V1 has a breadbasket for V3 being false, and there is no evidence that V1 is a course, then V1 and V2 have night time.
night_time(V1, V2) :- sandwich_shop(V1, V2), -cliffhanger(V1, V2), body_armor(V2), -breadbasket(V1, V3), not course(V1).

% Rule: r_61eba17473f2  |  line_index: 32  |  NL: If V1 and V2 have a palm, then V1 and V2 have a nit.
nit(V1, V2) :- palm(V1, V2).

% Rule: r_09c62d41d036  |  line_index: 33  |  NL: If V1 and V2 have a cliffhanger, then V1 and V2 have a palm.
palm(V1, V2) :- cliffhanger(V1, V2).

% Rule: r_3274c7ef5e4b  |  line_index: 34  |  NL: If V1 and V2 have a cliffhanger, then V2 is playing with friends.
playing_with_friends(V2) :- cliffhanger(V1, V2).