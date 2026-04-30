% Bundle: symtex_batch_20260428_225440Z_1204c702
% Rule: r_8d1801461453  |  line_index: 0  |  NL: P13 is explicitly false.
-p13.
% Rule: r_1a4ade819fc7  |  line_index: 1  |  NL: P14 is explicitly false.
-p14.
% Rule: r_730e9a9ec457  |  line_index: 2  |  NL: P17 is explicitly false.
-p17.
% Rule: r_1bbf1d441602  |  line_index: 3  |  NL: P18 is explicitly false.
-p18.
% Rule: r_e35abc6cb1c6  |  line_index: 4  |  NL: P21 is explicitly false.
-p21.
% Rule: r_0012d12df98f  |  line_index: 5  |  NL: P22 is explicitly false.
-p22.
% Rule: r_1e02c1f4e5da  |  line_index: 6  |  NL: P24 is explicitly false.
-p24.
% Rule: r_d0820e2bf91a  |  line_index: 7  |  NL: P26 is explicitly false.
-p26.
% Rule: r_e4b215614f6f  |  line_index: 8  |  NL: P15 is true.
p15.
% Rule: r_3c7f3d4071c9  |  line_index: 9  |  NL: P16 is true.
p16.
% Rule: r_e615b7c5b142  |  line_index: 10  |  NL: P19 is true.
p19.
% Rule: r_6e15cf7d3a13  |  line_index: 11  |  NL: P20 is true.
p20.
% Rule: r_12ae8b76637a  |  line_index: 12  |  NL: P25 is true.
p25.
% Rule: r_78647138daf8  |  line_index: 13  |  NL: P28 is true.
p28.
% Rule: r_701d84f1bc5b  |  line_index: 14  |  NL: P29 is true.
p29.
% Rule: r_f1ff08f82344  |  line_index: 15  |  NL: P30 is true.
p30.
% Rule: r_029c1b671e4d  |  line_index: 16  |  NL: If P1 is true, then P0 is explicitly false.
-p0 :- p1.
% Rule: r_234e2f2f35ce  |  line_index: 17  |  NL: If P15 is true and there is no evidence that P16 is explicitly false and there is no evidence that P17 is true, then P11 is explicitly false.
-p11 :- p15, not -p16, not p17.
% Rule: r_83ca67804be5  |  line_index: 18  |  NL: If P4 is true and P10 is explicitly false, then P12 is explicitly false.
-p12 :- p4, -p10.
% Rule: r_20ef37d9cfb7  |  line_index: 19  |  NL: If P5 is true, then P12 is explicitly false.
-p12 :- p5.
% Rule: r_76c66dd650ae  |  line_index: 20  |  NL: If P9 is explicitly false and there is no evidence that P11 is explicitly false and there is no evidence that P12 is true, then P15 is explicitly false.
-p15 :- -p9, not -p11, not p12.
% Rule: r_f130c2ed64e5  |  line_index: 21  |  NL: If P8 is explicitly false and P21 is explicitly false, then P20 is explicitly false.
-p20 :- -p8, -p21.
% Rule: r_5a9412063bf1  |  line_index: 22  |  NL: If P24 is explicitly false and there is no evidence that P25 is explicitly false and P26 is explicitly false, then P23 is explicitly false.
-p23 :- -p24, not -p25, -p26.
% Rule: r_70e2032da360  |  line_index: 23  |  NL: If P28 is true and P29 is true and there is no evidence that P30 is explicitly false, then P27 is explicitly false.
-p27 :- p28, p29, not -p30.
% Rule: r_752b932bc008  |  line_index: 24  |  NL: If P2 is true and there is no evidence that P6 is explicitly false, then P4 is explicitly false.
-p4 :- p2, not -p6.
% Rule: r_694634a2b951  |  line_index: 25  |  NL: If P14 is explicitly false, then P5 is explicitly false, P6 is true, or P7 is true.
-p5 | p6 | p7 :- -p14.
% Rule: r_c9daa220cf53  |  line_index: 26  |  NL: If P11 is true and there is no evidence that P22 is true, then P6 is explicitly false.
-p6 :- p11, not p22.
% Rule: r_b6361dd8db45  |  line_index: 27  |  NL: If P13 is explicitly false and there is no evidence that P17 is true, then P0 is true or P1 is explicitly false.
p0 | -p1 :- -p13, not p17.
% Rule: r_ff8b98a596a5  |  line_index: 28  |  NL: If P3 is true and there is no evidence that P9 is explicitly false and there is no evidence that P18 is true, then P10 is true.
p10 :- p3, not -p9, not p18.
% Rule: r_e9bb0d21e7fb  |  line_index: 29  |  NL: If P4 is explicitly false and there is no evidence that P19 is explicitly false and there is no evidence that P20 is explicitly false, then P12 is true.
p12 :- -p4, not -p19, not -p20.
% Rule: r_e296b2f73f52  |  line_index: 30  |  NL: If P10 is explicitly false, then P17 is true.
p17 :- -p10.
% Rule: r_7a6c79498207  |  line_index: 31  |  NL: If P0 is true and there is no evidence that P8 is explicitly false and there is no evidence that P10 is explicitly false, then P2 is true.
p2 :- p0, not -p8, not -p10.
% Rule: r_66e43c8693b8  |  line_index: 32  |  NL: If P1 is explicitly false and there is no evidence that P5 is true and there is no evidence that P11 is true, then P3 is true.
p3 :- -p1, not p5, not p11.
% Rule: r_7fead6f4ab0e  |  line_index: 33  |  NL: If there is no evidence that P5 is explicitly false and P12 is explicitly false, then P5 is true.
p5 :- not -p5, -p12.
% Rule: r_3b53629bd52d  |  line_index: 34  |  NL: If P7 is true, then P8 is true or P9 is true.
p8 | p9 :- p7.