- P11("Jeffery").
P12("Jonathan", "Jocelyn", "Jennifer").
- P13("Jonathan", "Jocelyn", "Jennifer").
- P14("Melissa", "Jennifer").
- P15("Melissa").
P16("Jeffery", "Jocelyn").
- P17("Jocelyn", "Melissa").
- P18("Jonathan", "Melissa", "Jennifer").
P10(V0, V3, V4) :- - P0(V0, V3), P2(V2, V4), P4(V3, V4), P6(V0, V1, V2), not -P8(V1, V3, V4).
- P0(V0, V3) :- - P11(V1), - P15(V3), P16(V1, V2), - P17(V2, V3), - P18(V0, V3, V4).
P1(V0, V2, V3) :- - P11(V1), - P15(V3), P16(V1, V2), - P17(V2, V3), - P18(V0, V3, V4).
P2(V2, V4) :- P12(V0, V2, V4).
- P3(V0, V2) :- P12(V0, V2, V4).
P4(V4, V4) :- P12(V0, V2, V4), not P13(V0, V2, V4).
- P5(V0, V2, V4) :- P12(V0, V2, V4), not P13(V0, V2, V4).
P6(V0, V2, V2) :- P1(V0, V2, V3), not -P7(V0, V2, V3).
P7(V0, V2, V2) :- - P3(V0, V2), not -P9(V0, V2).
P8(V3, V3, V4) :- P4(V3, V4), not P14(V3, V4).
P9(V0, V4) :- - P5(V0, V1, V4), - P14(V3, V4).