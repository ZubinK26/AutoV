% Bundle: symtex_batch_20260421_192951Z_f3e21224

% Domains
person(david).
person(michelle).
person(joe).
person(diana).
person(V) :- person(V).

% Rule: r_f9119c510d7c  |  line_index: 0  |  NL: The relationship P12 between David and Michelle is explicitly false.
-p12(david, michelle).

% Rule: r_75df3dd384ba  |  line_index: 1  |  NL: The relationship P15 between David and Michelle is explicitly false.
-p15(david, michelle).

% Rule: r_a2dc318141d2  |  line_index: 2  |  NL: The relationship P18 between David and Joe is explicitly false.
-p18(david, joe).

% Rule: r_73730d815e6b  |  line_index: 3  |  NL: The relationship P19 between David and Joe is explicitly false.
-p19(david, joe).

% Rule: r_873a7d874c45  |  line_index: 4  |  NL: The property P20 of Michelle is explicitly false.
-p20(michelle).

% Rule: r_e293e93fd778  |  line_index: 5  |  NL: The relationship P24 between David and Michelle is explicitly false.
-p24(david, michelle).

% Rule: r_2292f4e5cb99  |  line_index: 6  |  NL: The relationship P26 between David and Michelle is explicitly false.
-p26(david, michelle).

% Rule: r_41dee07507f7  |  line_index: 7  |  NL: The relationship P31 between David and Diana is explicitly false.
-p31(david, diana).

% Rule: r_bfc4c1a9138e  |  line_index: 8  |  NL: The relationship P32 between David and Joe is explicitly false.
-p32(david, joe).

% Rule: r_d93165433312  |  line_index: 9  |  NL: The property P13 of David is true.
p13(david).

% Rule: r_cb3d7c4974cb  |  line_index: 10  |  NL: The relationship P14 between David and Michelle is true.
p14(david, michelle).

% Rule: r_6a3ad1fc8fcf  |  line_index: 11  |  NL: The property P16 of Michelle is true.
p16(michelle).

% Rule: r_d626e38e9a4f  |  line_index: 12  |  NL: The relationship P17 between David and Michelle is true.
p17(david, michelle).

% Rule: r_cbe433634743  |  line_index: 13  |  NL: The property P21 of Michelle is true.
p21(michelle).

% Rule: r_2507978615f2  |  line_index: 14  |  NL: The property P22 of David is true.
p22(david).

% Rule: r_7227a3653020  |  line_index: 15  |  NL: The property P23 of David is true.
p23(david).

% Rule: r_d2c31df07c25  |  line_index: 16  |  NL: The property P28 of Diana is true.
p28(diana).

% Rule: r_e0926677d69f  |  line_index: 17  |  NL: The property P29 of Diana is true.
p29(diana).

% Rule: r_a5b293d2fcc6  |  line_index: 18  |  NL: The relationship P30 between David and Michelle is true.
p30(david, michelle).

% Rule: r_15365e271d38  |  line_index: 19  |  NL: If the relationship P12 between entity V0 and entity V1 is explicitly false, then the relationship P1 between V0 and V1 is explicitly false or the property P2 of V0 is true.
-p1(V0, V1) | p2(V0) :- -p12(V0, V1), person(V0), person(V1).

% Rule: r_6046bdc23c2f  |  line_index: 20  |  NL: If the property P0 of entity V1 is true and the relationship P3 between entity V0 and V1 is true and there is no evidence that the relationship P5 between V0 and V1 is true and there is no evidence that the relationship P9 between V0 and V1 is explicitly false, then the relationship P11 between V0 and V1 is explicitly false.
-p11(V0, V1) :- p0(V1), p3(V0, V1), not p5(V0, V1), not -p9(V0, V1), person(V0), person(V1).

% Rule: r_f6efbf06689b  |  line_index: 21  |  NL: If there is no evidence that the property P2 of entity V0 is true and there is no evidence that the property P4 of entity V1 is explicitly false and the relationship P6 between V0 and V1 is explicitly false and the property P8 of V1 is explicitly false and there is no evidence that the relationship P11 between V0 and V1 is explicitly false, then the property P16 of V1 is explicitly false.
-p16(V1) :- not p2(V0), not -p4(V1), -p6(V0, V1), -p8(V1), not -p11(V0, V1), person(V0), person(V1).

% Rule: r_6d97a0913014  |  line_index: 22  |  NL: If the relationship P1 between entity V0 and entity V1 is true and the relationship P3 between V0 and V1 is explicitly false and the relationship P6 between V0 and V1 is explicitly false and the relationship P24 between V0 and V1 is explicitly false, then the property P2 of V0 is explicitly false.
-p2(V0) :- p1(V0, V1), -p3(V0, V1), -p6(V0, V1), -p24(V0, V1), person(V0), person(V1).

% Rule: r_50199b02c59e  |  line_index: 23  |  NL: If the property P28 of entity V2 is true and the property P29 of V2 is true and the relationship P30 between entity V0 and entity V1 is true and the relationship P31 between V0 and V2 is explicitly false and the relationship P32 between V0 and entity V3 is explicitly false, then the property P27 of V3 is explicitly false.
-p27(V3) :- p28(V2), p29(V2), p30(V0, V1), -p31(V0, V2), -p32(V0, V3), person(V0), person(V1), person(V2), person(V3).

% Rule: r_c9dd038f940d  |  line_index: 24  |  NL: If the property P4 of entity V1 is explicitly false and there is no evidence that the property P7 of V1 is true and there is no evidence that the property P10 of V1 is true and there is no evidence that the property P20 of V1 is true and there is no evidence that the property P21 of V1 is explicitly false, then the relationship P5 between V1 and V1 is explicitly false.
-p5(V1, V1) :- -p4(V1), not p7(V1), not p10(V1), not p20(V1), not -p21(V1), person(V1).

% Rule: r_affbaca6e963  |  line_index: 25  |  NL: If the relationship P1 between entity V0 and entity V1 is explicitly false and there is no evidence that the relationship P6 between V0 and V1 is explicitly false and there is no evidence that the relationship P9 between V0 and V1 is explicitly false and there is no evidence that the relationship P14 between V0 and V1 is explicitly false and there is no evidence that the relationship P15 between V0 and V1 is true, then the property P0 of V1 is true.
p0(V1) :- -p1(V0, V1), not -p6(V0, V1), not -p9(V0, V1), not -p14(V0, V1), not p15(V0, V1), person(V0), person(V1).

% Rule: r_a8906181db3f  |  line_index: 26  |  NL: If the relationship P1 between entity V0 and entity V1 is true and the property P7 of V1 is true and the property P10 of V1 is true, then the relationship P11 between V0 and V1 is true.
p11(V0, V1) :- p1(V0, V1), p7(V1), p10(V1), person(V0), person(V1).

% Rule: r_49a0a44df292  |  line_index: 27  |  NL: If the property P4 of entity V1 is true, then the relationship P11 between V1 and V1 is true.
p11(V1, V1) :- p4(V1), person(V1).

% Rule: r_7d214733c4c5  |  line_index: 28  |  NL: If the property P0 of entity V1 is explicitly false and there is no evidence that the property P2 of entity V0 is true and the relationship P6 between V0 and V1 is explicitly false and there is no evidence that the property P10 of V1 is explicitly false and there is no evidence that the relationship P11 between V0 and V1 is explicitly false, then the relationship P18 between V0 and V1 is true.
p18(V0, V1) :- -p0(V1), not p2(V0), -p6(V0, V1), not -p10(V1), not -p11(V0, V1), person(V0), person(V1).

% Rule: r_792f8b1e00a9  |  line_index: 29  |  NL: If the property P8 of entity V1 is explicitly false, then the property P20 of V1 is true.
p20(V1) :- -p8(V1), person(V1).

% Rule: r_02ab4c965950  |  line_index: 30  |  NL: If there is no evidence that the property P0 of entity V1 is true and the relationship P1 between entity V0 and V1 is true and there is no evidence that the relationship P6 between V0 and V1 is true and the relationship P9 between V0 and V1 is explicitly false and there is no evidence that the property P10 of V1 is explicitly false, then the property P20 of V1 is true.
p20(V1) :- not p0(V1), p1(V0, V1), not p6(V0, V1), -p9(V0, V1), not -p10(V1), person(V0), person(V1).

% Rule: r_b85c5a2e6978  |  line_index: 31  |  NL: If the relationship P26 between entity V0 and entity V1 is explicitly false, then the relationship P25 between V0 and V1 is true.
p25(V0, V1) :- -p26(V0, V1), person(V0), person(V1).

% Rule: r_3409da2241b7  |  line_index: 32  |  NL: If the property P13 of entity V0 is true and the property P16 of entity V1 is true and the relationship P17 between V0 and V1 is true and the relationship P18 between V0 and entity V3 is explicitly false and there is no evidence that the relationship P19 between V0 and V3 is true, then the relationship P3 between V0 and V1 is true or the property P4 of V1 is explicitly false.
p3(V0, V1) | -p4(V1) :- p13(V0), p16(V1), p17(V0, V1), -p18(V0, V3), not p19(V0, V3), person(V0), person(V1), person(V3).

% Rule: r_57ac0f30fbee  |  line_index: 33  |  NL: If the property P4 of entity V1 is true, then the relationship P5 between V1 and V1 is true.
p5(V1, V1) :- p4(V1), person(V1).

% Rule: r_f26261f75b27  |  line_index: 34  |  NL: If the property P2 of entity V0 is true and there is no evidence that the property P22 of V0 is explicitly false and there is no evidence that the property P23 of V0 is explicitly false, then the relationship P6 between V0 and V0 is true or the property P7 of V0 is explicitly false or the property P8 of V0 is true.
p6(V0, V0) | -p7(V0) | p8(V0) :- p2(V0), not -p22(V0), not -p23(V0), person(V0).

% Rule: r_080e1980669c  |  line_index: 35  |  NL: If the property P8 of entity V1 is true, then the relationship P9 between V1 and V1 is true or the property P10 of V1 is explicitly false.
p9(V1, V1) | -p10(V1) :- p8(V1), person(V1).