- P12("David", "Michelle").
- P15("David", "Michelle").
- P18("David", "Joe").
- P19("David", "Joe").
- P20("Michelle").
- P24("David", "Michelle").
- P26("David", "Michelle").
- P31("David", "Diana").
- P32("David", "Joe").
P13("David").
P14("David", "Michelle").
P16("Michelle").
P17("David", "Michelle").
P21("Michelle").
P22("David").
P23("David").
P28("Diana").
P29("Diana").
P30("David", "Michelle").
- P1(V0, V1) | P2(V0) :- - P12(V0, V1).
- P11(V0, V1) :- P0(V1), P3(V0, V1), not P5(V0, V1), not -P9(V0, V1).
- P16(V1) :- not P2(V0), not -P4(V1), - P6(V0, V1), - P8(V1), not -P11(V0, V1).
- P2(V0) :- P1(V0, V1), - P3(V0, V1), - P6(V0, V1), - P24(V0, V1).
- P27(V3) :- P28(V2), P29(V2), P30(V0, V1), - P31(V0, V2), - P32(V0, V3).
- P5(V1, V1) :- - P4(V1), not P7(V1), not P10(V1), not P20(V1), not -P21(V1).
P0(V1) :- - P1(V0, V1), not -P6(V0, V1), not -P9(V0, V1), not -P14(V0, V1), not P15(V0, V1).
P11(V0, V1) :- P1(V0, V1), P7(V1), P10(V1).
P11(V1, V1) :- P4(V1).
P18(V0, V1) :- - P0(V1), not P2(V0), - P6(V0, V1), not -P10(V1), not -P11(V0, V1).
P20(V1) :- - P8(V1).
P20(V1) :- not P0(V1), P1(V0, V1), not P6(V0, V1), - P9(V0, V1), not -P10(V1).
P25(V0, V1) :- - P26(V0, V1).
P3(V0, V1) | - P4(V1) :- P13(V0), P16(V1), P17(V0, V1), - P18(V0, V3), not P19(V0, V3).
P5(V1, V1) :- P4(V1).
P6(V0, V0) | - P7(V0) | P8(V0) :- P2(V0), not -P22(V0), not -P23(V0).
P9(V1, V1) | - P10(V1) :- P8(V1).