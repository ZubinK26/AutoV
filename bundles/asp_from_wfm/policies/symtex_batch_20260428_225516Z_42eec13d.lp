% Bundle: symtex_batch_20260428_225516Z_42eec13d
% Rule: r_640629637aab  |  line_index: 9  |  NL: If P1(V0, V1, V2) is true and P3(V0, V1, V3) is true and P4(V0, V1, V3) is true, then P6(V2) is true.
p6(V2) :- p1(V0, V1, V2), p3(V0, V1, V3), p4(V0, V1, V3).
% Rule: r_af3bcb4668f2  |  line_index: 10  |  NL: If P7(V0, V3) is true and P13(V0, MAX_V2, V4) is true and P14(V2, V3, V4) is true, then P0(V0, V2, V4) is true.
p0(V0, V2, V4) :- p7(V0, V3), p13(V0, MAX_V2, V4), p14(V2, V3, V4).
% Rule: r_cb58fd8ac42f  |  line_index: 11  |  NL: If P0(V0, V2, V4) is true and P5(V0, V2, V4) is true and P12(V0, V2, V4) is true, then P1(V0, V2, V2) is true.
p1(V0, V2, V2) :- p0(V0, V2, V4), p5(V0, V2, V4), p12(V0, V2, V4).
% Rule: r_d24e30a4f4ae  |  line_index: 12  |  NL: If P8(V0, V2, V4) is true and P10(V0, V2, V4) is true and P12(V0, V2, V4) is true, then P2(V2, V4) is true.
p2(V2, V4) :- p8(V0, V2, V4), p10(V0, V2, V4), p12(V0, V2, V4).
% Rule: r_c3d04993939c  |  line_index: 13  |  NL: If P2(V1, V4) is true and P13(V0, V2, V4) is true and P15(V0, V2, V4) is true, then P3(V0, V1, V1) is true.
p3(V0, V1, V1) :- p2(V1, V4), p13(V0, V2, V4), p15(V0, V2, V4).
% Rule: r_50eb45a2a925  |  line_index: 14  |  NL: If P9(V0, V2, V4) is true and P10(V0, V2, V4) is true and P11(V0, V2, V4) is true, then P4(V0, V2, V4) is true.
p4(V0, V2, V4) :- p9(V0, V2, V4), p10(V0, V2, V4), p11(V0, V2, V4).
% Rule: r_0e21ed219ea4  |  line_index: 15  |  NL: If P9(V0, V2, V4) is true and P10(V0, V2, V4) is true and P11(V0, V2, V4) is true, then P5(V0, V2, V4) is true.
p5(V0, V2, V4) :- p9(V0, V2, V4), p10(V0, V2, V4), p11(V0, V2, V4).