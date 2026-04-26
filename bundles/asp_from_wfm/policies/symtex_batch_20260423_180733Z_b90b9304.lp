% Bundle: symtex_batch_20260423_180733Z_b90b9304

person("Chris").
person("Steven").
person("Kevin").
person("Tracey").

% Rule: r_09d8d72c0787  |  line_index: 0  |  NL: P12('Chris') is explicitly false.
-p12("Chris").

% Rule: r_88bdbc28959e  |  line_index: 1  |  NL: P13('Chris', 'Steven') is true.
p13("Chris", "Steven").

% Rule: r_7016a6349ad0  |  line_index: 2  |  NL: P14('Chris', 'Steven') is explicitly false.
-p14("Chris", "Steven").

% Rule: r_501f1a1c5d97  |  line_index: 3  |  NL: P15 is explicitly false.
-p15.

% Rule: r_15d3cc74c3f4  |  line_index: 4  |  NL: P16('Chris', 'Tracey') is explicitly false.
-p16("Chris", "Tracey").

% Rule: r_28316609a16b  |  line_index: 5  |  NL: P17('Chris', 'Steven') is true.
p17("Chris", "Steven").

% Rule: r_058e69708b1d  |  line_index: 6  |  NL: P18('Chris', 'Steven') is explicitly false.
-p18("Chris", "Steven").

% Rule: r_7fd73d59d00f  |  line_index: 7  |  NL: P19('Chris', 'Steven') is explicitly false.
-p19("Chris", "Steven").

% Rule: r_c3caebe2997b  |  line_index: 8  |  NL: P20('Steven', 'Kevin') is explicitly false.
-p20("Steven", "Kevin").

% Rule: r_62e402a05550  |  line_index: 9  |  NL: P21('Steven', 'Kevin') is true.
p21("Steven", "Kevin").

% Rule: r_bb37e725641f  |  line_index: 10  |  NL: P22('Steven', 'Kevin') is true.
p22("Steven", "Kevin").

% Rule: r_f77a8077c324  |  line_index: 11  |  NL: P23('Chris', 'Kevin') is true.
p23("Chris", "Kevin").

% Rule: r_be59956ed8ea  |  line_index: 12  |  NL: P24('Steven', 'Tracey') is explicitly false.
-p24("Steven", "Tracey").

% Rule: r_e33f3d7772cf  |  line_index: 13  |  NL: If P2(V0, V3) is explicitly false and P4(V1, V2) is true and there is no evidence that P6(V2, V3) is explicitly false, then P11(V1, V2) is true.
p11(V1, V2) :- -p2(V0, V3), p4(V1, V2), not -p6(V2, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_424f681f03ac  |  line_index: 14  |  NL: If P12(V0) is explicitly false and P19(V0, V1) is explicitly false and P20(V1, V3) is explicitly false and there is no evidence that P21(V1, V3) is explicitly false and there is no evidence that P22(V1, V3) is explicitly false, then P0(V0, V1) is explicitly false.
-p0(V0, V1) :- -p12(V0), -p19(V0, V1), -p20(V1, V3), not -p21(V1, V3), not -p22(V1, V3), person(V0), person(V1), person(V3).

% Rule: r_4860271abbdc  |  line_index: 15  |  NL: If P12(V0) is explicitly false and P19(V0, V1) is explicitly false and P20(V1, V3) is explicitly false and there is no evidence that P21(V1, V3) is explicitly false and there is no evidence that P22(V1, V3) is explicitly false, then P1(V0, V1) is true.
p1(V0, V1) :- -p12(V0), -p19(V0, V1), -p20(V1, V3), not -p21(V1, V3), not -p22(V1, V3), person(V0), person(V1), person(V3).

% Rule: r_aefa4b81fbea  |  line_index: 16  |  NL: If P0(V0, V1) is explicitly false and there is no evidence that P3(V0, V1) is true and there is no evidence that P5(V0, V1) is explicitly false and there is no evidence that P7(V0, V1) is true and there is no evidence that P10(V0, V1) is true, then P2(V0, V1) is explicitly false.
-p2(V0, V1) :- -p0(V0, V1), not p3(V0, V1), not -p5(V0, V1), not p7(V0, V1), not p10(V0, V1), person(V0), person(V1).

% Rule: r_c8c1be1fb559  |  line_index: 17  |  NL: If P13(V0, V1) is true, then P3(V0, V1) is explicitly false.
-p3(V0, V1) :- p13(V0, V1), person(V0), person(V1).

% Rule: r_6fa0fe22b598  |  line_index: 18  |  NL: If P14(V0, V1) is explicitly false and P23(V0, V3) is true and P24(V1, V2) is explicitly false, then P4(V1, V2) is true.
p4(V1, V2) :- -p14(V0, V1), p23(V0, V3), -p24(V1, V2), person(V0), person(V1), person(V2), person(V3).

% Rule: r_70b210bc6f6e  |  line_index: 19  |  NL: If P14(V0, V1) is explicitly false and P23(V0, V3) is true and P24(V1, V2) is explicitly false, then P5(V0, V1) is true.
p5(V0, V1) :- -p14(V0, V1), p23(V0, V3), -p24(V1, V2), person(V0), person(V1), person(V2), person(V3).

% Rule: r_bc38bbccc638  |  line_index: 20  |  NL: If P13(V0, V1) is true and there is no evidence that P15 is true, then P6(V0, V0) is true.
p6(V0, V0) :- p13(V0, V1), not p15, person(V0), person(V1).

% Rule: r_c7f2f53e9401  |  line_index: 21  |  NL: If P13(V0, V1) is true and there is no evidence that P15 is true, then P7(V0, V1) is explicitly false.
-p7(V0, V1) :- p13(V0, V1), not p15, person(V0), person(V1).

% Rule: r_7b6b199b83fe  |  line_index: 22  |  NL: If P13(V0, V1) is true and there is no evidence that P15 is true, then P8(V1, V0) is true.
p8(V1, V0) :- p13(V0, V1), not p15, person(V0), person(V1).

% Rule: r_fdf182135281  |  line_index: 23  |  NL: If P16(V0, V2) is explicitly false, then P9(V0, V2) is explicitly false.
-p9(V0, V2) :- -p16(V0, V2), person(V0), person(V2).

% Rule: r_18de25c8cd43  |  line_index: 24  |  NL: If P1(V0, V1) is true and P8(V1, V3) is true and P9(V0, V2) is explicitly false and there is no evidence that P17(V0, V1) is explicitly false and there is no evidence that P18(V0, V1) is true, then P10(V0, V1) is explicitly false.
-p10(V0, V1) :- p1(V0, V1), p8(V1, V3), -p9(V0, V2), not -p17(V0, V1), not p18(V0, V1), person(V0), person(V1), person(V2), person(V3).