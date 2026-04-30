P7("Antonio", "Crystal").
P8("Antonio", "Brandon", "Selena").
P9("Antonio", "Brandon", "Selena").
P10("Antonio", "Brandon", "Selena").
P11("Antonio", "Brandon", "Selena").
P12("Antonio", "Brandon", "Selena").
P13("Antonio", "Brandon", "Selena").
P14("Brandon", "Crystal", "Selena").
P15("Antonio", "Brandon", "Selena").
P6(V2) :- P1(V0, V1, V2), P3(V0, V1, V3), P4(V0, V1, V3).
P0(V0, V2, V4) :- P7(V0, V3), P13(V0, V2, V4), P14(V2, V3, V4).
P1(V0, V2, V2) :- P0(V0, V2, V4), P5(V0, V2, V4), P12(V0, V2, V4).
P2(V2, V4) :- P8(V0, V2, V4), P10(V0, V2, V4), P12(V0, V2, V4).
P3(V0, V1, V1) :- P2(V1, V4), P13(V0, V2, V4), P15(V0, V2, V4).
P4(V0, V2, V4) :- P9(V0, V2, V4), P10(V0, V2, V4), P11(V0, V2, V4).
P5(V0, V2, V4) :- P9(V0, V2, V4), P10(V0, V2, V4), P11(V0, V2, V4).