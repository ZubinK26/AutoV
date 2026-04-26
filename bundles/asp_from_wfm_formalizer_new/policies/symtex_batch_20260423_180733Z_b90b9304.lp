% Bundle: symtex_batch_20260423_180733Z_b90b9304
% Rule: r_f704902c3219  |  line_index: 0  |  NL: P12('Chris') is explicitly false.
-p12("Chris").
% Rule: r_ea8123f57ecf  |  line_index: 1  |  NL: P13('Chris', 'Steven') is true.
p13("Chris", "Steven").
% Rule: r_7f25f94b6ea5  |  line_index: 2  |  NL: P14('Chris', 'Steven') is explicitly false.
-p14("Chris", "Steven").
% Rule: r_88dc241bed39  |  line_index: 3  |  NL: P15 is explicitly false.
-p15.
% Rule: r_b61f55d043da  |  line_index: 4  |  NL: P16('Chris', 'Tracey') is explicitly false.
-p16("Chris", "Tracey").
% Rule: r_a1823eaa6001  |  line_index: 5  |  NL: P17('Chris', 'Steven') is true.
p17("Chris", "Steven").
% Rule: r_f64781200072  |  line_index: 6  |  NL: P18('Chris', 'Steven') is explicitly false.
-p18("Chris", "Steven").
% Rule: r_bbc816839c1a  |  line_index: 7  |  NL: P19('Chris', 'Steven') is explicitly false.
-p19("Chris", "Steven").
% Rule: r_f92def74e3a6  |  line_index: 8  |  NL: P20('Steven', 'Kevin') is explicitly false.
-p20("Steven", "Kevin").
% Rule: r_9995713abc7e  |  line_index: 9  |  NL: P21('Steven', 'Kevin') is true.
p21("Steven", "Kevin").
% Rule: r_df86a38dda81  |  line_index: 10  |  NL: P22('Steven', 'Kevin') is true.
p22("Steven", "Kevin").
% Rule: r_1461b6fb93da  |  line_index: 11  |  NL: P23('Chris', 'Kevin') is true.
p23("Chris", "Kevin").
% Rule: r_39b1543bfcc3  |  line_index: 12  |  NL: P24('Steven', 'Tracey') is explicitly false.
-p24("Steven", "Tracey").
% Rule: r_0c8e692c66e1  |  line_index: 13  |  NL: If P2(V0, V3) is explicitly false and P4(V1, V2) is true and there is no evidence that P6(V2, V3) is explicitly false, then P11(V1, V2) is true.
p11(V1, V2) :- -p2(V0, V3), p4(V1, V2), not -p6(V2, V3).
% Rule: r_7bee1e32f47a  |  line_index: 14  |  NL: If P12(V0) is explicitly false and P19(V0, V1) is explicitly false and P20(V1, V3) is explicitly false and there is no evidence that P21(V1, V3) is explicitly false and there is no evidence that P22(V1, V3) is explicitly false, then P0(V0, V1) is explicitly false.
-p0(V0, V1) :- -p12(V0), -p19(V0, V1), -p20(V1, V3), not -p21(V1, V3), not -p22(V1, V3).
% Rule: r_6bec3f911105  |  line_index: 15  |  NL: If P12(V0) is explicitly false and P19(V0, V1) is explicitly false and P20(V1, V3) is explicitly false and there is no evidence that P21(V1, V3) is explicitly false and there is no evidence that P22(V1, V3) is explicitly false, then P1(V0, V1) is true.
p1(V0, V1) :- -p12(V0), -p19(V0, V1), -p20(V1, V3), not -p21(V1, V3), not -p22(V1, V3).
% Rule: r_2d2dce9962de  |  line_index: 16  |  NL: If P0(V0, V1) is explicitly false and there is no evidence that P3(V0, V1) is true and there is no evidence that P5(V0, V1) is explicitly false and there is no evidence that P7(V0, V1) is true and there is no evidence that P10(V0, V1) is true, then P2(V0, V1) is explicitly false.
-p2(V0, V1) :- -p0(V0, V1), not p3(V0, V1), not -p5(V0, V1), not p7(V0, V1), not p10(V0, V1).
% Rule: r_8541530587c3  |  line_index: 17  |  NL: If P13(V0, V1) is true, then P3(V0, V1) is explicitly false.
-p3(V0, V1) :- p13(V0, V1).
% Rule: r_ed0d64a39782  |  line_index: 18  |  NL: If P14(V0, V1) is explicitly false and P23(V0, V3) is true and P24(V1, V2) is explicitly false, then P4(V1, V2) is true.
p4(V1, V2) :- -p14(V0, V1), p23(V0, V3), -p24(V1, V2).
% Rule: r_f45773786c99  |  line_index: 19  |  NL: If P14(V0, V1) is explicitly false and P23(V0, V3) is true and P24(V1, V2) is explicitly false, then P5(V0, V1) is true.
p5(V0, V1) :- -p14(V0, V1), p23(V0, V3), -p24(V1, V2).
% Rule: r_6cecf98bf951  |  line_index: 20  |  NL: If P13(V0, V1) is true and there is no evidence that P15 is true, then P6(V0, V0) is true.
p6(V0, V0) :- p13(V0, V1), not p15.
% Rule: r_c9028926aab2  |  line_index: 21  |  NL: If P13(V0, V1) is true and there is no evidence that P15 is true, then P7(V0, V1) is explicitly false.
-p7(V0, V1) :- p13(V0, V1), not p15.
% Rule: r_ec2d9caa1bed  |  line_index: 22  |  NL: If P13(V0, V1) is true and there is no evidence that P15 is true, then P8(V1, V0) is true.
p8(V1, V0) :- p13(V0, V1), not p15.
% Rule: r_5522cab022c5  |  line_index: 23  |  NL: If P16(V0, V2) is explicitly false, then P9(V0, V2) is explicitly false.
-p9(V0, V2) :- -p16(V0, V2).
% Rule: r_15b7d74dd651  |  line_index: 24  |  NL: If P1(V0, V1) is true and P8(V1, V3) is true and P9(V0, V2) is explicitly false and there is no evidence that P17(V0, V1) is explicitly false and there is no evidence that P18(V0, V1) is true, then P10(V0, V1) is explicitly false.
-p10(V0, V1) :- p1(V0, V1), p8(V1, V3), -p9(V0, V2), not -p17(V0, V1), not p18(V0, V1).