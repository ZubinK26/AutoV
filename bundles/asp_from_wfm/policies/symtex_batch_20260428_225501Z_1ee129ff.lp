% Bundle: symtex_batch_20260428_225501Z_1ee129ff
% Rule: r_e1bbf3317ae1  |  line_index: 0  |  NL: P11(Jeffery) is explicitly false.
-p11(jeffery).
% Rule: r_0ebffcf34ff0  |  line_index: 1  |  NL: P12(Jonathan, Jocelyn, Jennifer) is true.
p12(jonathan, jocelyn, jennifer).
% Rule: r_9f3a960656f8  |  line_index: 2  |  NL: P13(Jonathan, Jocelyn, Jennifer) is explicitly false.
-p13(jonathan, jocelyn, jennifer).
% Rule: r_a4f247b11837  |  line_index: 3  |  NL: P14(Melissa, Jennifer) is explicitly false.
-p14(melissa, jennifer).
% Rule: r_4a199ef53e1e  |  line_index: 4  |  NL: P15(Melissa) is explicitly false.
-p15(melissa).
% Rule: r_9b016cd81601  |  line_index: 5  |  NL: P16(Jeffery, Jocelyn) is true.
p16(jeffery, jocelyn).
% Rule: r_852374468779  |  line_index: 6  |  NL: P17(Jocelyn, Melissa) is explicitly false.
-p17(jocelyn, melissa).
% Rule: r_3b81919e0192  |  line_index: 7  |  NL: P18(Jonathan, Melissa, Jennifer) is explicitly false.
-p18(jonathan, melissa, jennifer).
% Rule: r_8bae13fb1764  |  line_index: 8  |  NL: If P0(V0, V3) is explicitly false and P2(V2, V4) is true and P4(V3, V4) is true and P6(V0, V1, V2) is true and there is no evidence that P8(V1, V3, V4) is explicitly false, then P10(V0, V3, V4) is true.
p10(V0, V3, V4) :- -p0(V0, V3), p2(V2, V4), p4(V3, V4), p6(V0, V1, V2), not -p8(V1, V3, V4).
% Rule: r_b291ab488b88  |  line_index: 9  |  NL: If P11(V1) is explicitly false and P15(V3) is explicitly false and P16(V1, V2) is true and P17(V2, V3) is explicitly false and P18(V0, V3, V4) is explicitly false, then P0(V0, V3) is explicitly false.
-p0(V0, V3) :- -p11(V1), -p15(V3), p16(V1, V2), -p17(V2, V3), -p18(V0, V3, V4).
% Rule: r_c446caadefb0  |  line_index: 10  |  NL: If P11(V1) is explicitly false and P15(V3) is explicitly false and P16(V1, V2) is true and P17(V2, V3) is explicitly false and P18(V0, V3, V4) is explicitly false, then P1(V0, V2, V3) is true.
p1(V0, V2, V3) :- -p11(V1), -p15(V3), p16(V1, V2), -p17(V2, V3), -p18(V0, V3, V4).
% Rule: r_57adb1fd17ed  |  line_index: 11  |  NL: If P12(V0, V2, V4) is true, then P2(V2, V4) is true.
p2(V2, V4) :- p12(V0, V2, V4).
% Rule: r_77ffed7a1a6d  |  line_index: 12  |  NL: If P12(V0, V2, V4) is true, then P3(V0, V2) is explicitly false.
-p3(V0, V2) :- p12(V0, V2, V4).
% Rule: r_f64a17d1f1bd  |  line_index: 13  |  NL: If P12(V0, V2, V4) is true and there is no evidence that P13(V0, V2, V4) is true, then P4(V4, V4) is true.
p4(V4, V4) :- p12(V0, V2, V4), not p13(V0, V2, V4).
% Rule: r_a1da79e78365  |  line_index: 14  |  NL: If P12(V0, V2, V4) is true and there is no evidence that P13(V0, V2, V4) is true, then P5(V0, V2, V4) is explicitly false.
-p5(V0, V2, V4) :- p12(V0, V2, V4), not p13(V0, V2, V4).
% Rule: r_b85f7c1b0fa6  |  line_index: 15  |  NL: If P1(V0, V2, V3) is true and there is no evidence that P7(V0, V2, V3) is explicitly false, then P6(V0, V2, V2) is true.
p6(V0, V2, V2) :- p1(V0, V2, V3), not -p7(V0, V2, V3).
% Rule: r_4a7a637633eb  |  line_index: 16  |  NL: If P3(V0, V2) is explicitly false and there is no evidence that P9(V0, V2) is explicitly false, then P7(V0, V2, V2) is true.
p7(V0, V2, V2) :- -p3(V0, V2), not -p9(V0, V2).
% Rule: r_df45a68d404e  |  line_index: 17  |  NL: If P4(V3, V4) is true and there is no evidence that P14(V3, V4) is true, then P8(V3, V3, V4) is true.
p8(V3, V3, V4) :- p4(V3, V4), not p14(V3, V4).
% Rule: r_8cb7c1639b19  |  line_index: 18  |  NL: If P5(V0, V1, V4) is explicitly false and P14(V3, V4) is explicitly false, then P9(V0, V4) is true.
p9(V0, V4) :- -p5(V0, V1, V4), -p14(V3, V4).