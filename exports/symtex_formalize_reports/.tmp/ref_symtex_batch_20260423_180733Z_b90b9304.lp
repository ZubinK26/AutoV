- P12("Chris").
P13("Chris", "Steven").
- P14("Chris", "Steven").
- P15.
- P16("Chris", "Tracey").
P17("Chris", "Steven").
- P18("Chris", "Steven").
- P19("Chris", "Steven").
- P20("Steven", "Kevin").
P21("Steven", "Kevin").
P22("Steven", "Kevin").
P23("Chris", "Kevin").
- P24("Steven", "Tracey").
P11(V1, V2) :- - P2(V0, V3), P4(V1, V2), not -P6(V2, V3).
- P0(V0, V1) :- - P12(V0), - P19(V0, V1), - P20(V1, V3), not -P21(V1, V3), not -P22(V1, V3).
P1(V0, V1) :- - P12(V0), - P19(V0, V1), - P20(V1, V3), not -P21(V1, V3), not -P22(V1, V3).
- P2(V0, V1) :- - P0(V0, V1), not P3(V0, V1), not -P5(V0, V1), not P7(V0, V1), not P10(V0, V1).
- P3(V0, V1) :- P13(V0, V1).
P4(V1, V2) :- - P14(V0, V1), P23(V0, V3), - P24(V1, V2).
P5(V0, V1) :- - P14(V0, V1), P23(V0, V3), - P24(V1, V2).
P6(V0, V0) :- P13(V0, V1), not P15.
- P7(V0, V1) :- P13(V0, V1), not P15.
P8(V1, V0) :- P13(V0, V1), not P15.
- P9(V0, V2) :- - P16(V0, V2).
- P10(V0, V1) :- P1(V0, V1), P8(V1, V3), - P9(V0, V2), not -P17(V0, V1), not P18(V0, V1).