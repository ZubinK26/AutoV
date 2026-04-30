% Bundle: symtex_batch_20260428_225559Z_c2f62e4a
person("Kevin"). person("Jenny"). person("Katelyn"). person("Alexander"). person("Mariah").
% Rule: r_69aa3b1c328e  |  line_index: 0  |  NL: The relationship army('Kevin', 'Jenny', 'Katelyn') is explicitly false.
-army("Kevin", "Jenny", "Katelyn").
% Rule: r_595286a087df  |  line_index: 1  |  NL: The relationship canary_yellow('Alexander', 'Mariah', 'Katelyn') is explicitly false.
-canary_yellow("Alexander", "Mariah", "Katelyn").
% Rule: r_6e2d8863cc84  |  line_index: 2  |  NL: The relationship cotton('Kevin', 'Jenny', 'Katelyn') is explicitly false.
-cotton("Kevin", "Jenny", "Katelyn").
% Rule: r_99df53526887  |  line_index: 3  |  NL: The relationship sanguine('Alexander', 'Katelyn') is explicitly false.
-sanguine("Alexander", "Katelyn").
% Rule: r_240daa8a1570  |  line_index: 4  |  NL: The relationship scarlet('Kevin', 'Jenny', 'Mariah') is explicitly false.
-scarlet("Kevin", "Jenny", "Mariah").
% Rule: r_ebd36c822257  |  line_index: 5  |  NL: The relationship school_cafeteria('Kevin', 'Alexander', 'Katelyn') is explicitly false.
-school_cafeteria("Kevin", "Alexander", "Katelyn").
% Rule: r_64599416f00e  |  line_index: 6  |  NL: The relationship sheep('Alexander', 'Jenny') is explicitly false.
-sheep("Alexander", "Jenny").
% Rule: r_f94844a98d66  |  line_index: 7  |  NL: The relationship spring('Kevin', 'Mariah', 'Katelyn') is explicitly false.
-spring("Kevin", "Mariah", "Katelyn").
% Rule: r_b9099e72be8b  |  line_index: 8  |  NL: The relationship turkey_red('Jenny', 'Mariah') is explicitly false.
-turkey_red("Jenny", "Mariah").
% Rule: r_2fdf35715685  |  line_index: 9  |  NL: The relationship gentle('Kevin', 'Jenny', 'Katelyn') is true.
gentle("Kevin", "Jenny", "Katelyn").
% Rule: r_bbd8962691db  |  line_index: 10  |  NL: The relationship lens('Alexander', 'Jenny', 'Mariah') is true.
lens("Alexander", "Jenny", "Mariah").
% Rule: r_a759dce5d359  |  line_index: 11  |  NL: The relationship light_brown('Kevin', 'Alexander', 'Jenny') is true.
light_brown("Kevin", "Alexander", "Jenny").
% Rule: r_06c2df7a69e8  |  line_index: 12  |  NL: The relationship radio('Kevin', 'Jenny', 'Katelyn') is true.
radio("Kevin", "Jenny", "Katelyn").
% Rule: r_c4fc35b23640  |  line_index: 13  |  NL: The relationship redtail('Kevin', 'Alexander', 'Jenny') is true.
redtail("Kevin", "Alexander", "Jenny").
% Rule: r_defdb45ba451  |  line_index: 14  |  NL: The relationship wool('Kevin', 'Alexander', 'Mariah') is true.
wool("Kevin", "Alexander", "Mariah").
% Rule: r_acd262fe66f8  |  line_index: 15  |  NL: If brown(V0, V1, V2) is true and red(V0, V3, V4) is explicitly false, then blue(V1, V3, V4) is explicitly false.
-blue(V1, V3, V4) :- brown(V0, V1, V2), -red(V0, V3, V4).
% Rule: r_a6967c46db4b  |  line_index: 16  |  NL: If yellow(V1, V3, V4) is explicitly false and blue(V1, V3, V4) is true and brown(V0, V1, V2) is explicitly false and there is no evidence that red(V0, V3, V4) is explicitly false, then chromatic_color(V3) is explicitly false.
-chromatic_color(V3) :- -yellow(V1, V3, V4), blue(V1, V3, V4), -brown(V0, V1, V2), not -red(V0, V3, V4).
% Rule: r_70cd96b012a7  |  line_index: 17  |  NL: If yellow(V1, V3, V4) is explicitly false and there is no evidence that blue(V1, V3, V4) is explicitly false, then chromatic_color(V3) is explicitly false.
-chromatic_color(V3) :- -yellow(V1, V3, V4), not -blue(V1, V3, V4).
% Rule: r_76f5d1683327  |  line_index: 18  |  NL: If yellow(V1, V3, V4) is explicitly false and brown(V0, V1, V2) is explicitly false and there is no evidence that red(V0, V3, V4) is explicitly false, then light_brown(V0, V1, V2) is explicitly false.
-light_brown(V0, V1, V2) :- -yellow(V1, V3, V4), -brown(V0, V1, V2), not -red(V0, V3, V4).
% Rule: r_2d3ad94bdc71  |  line_index: 19  |  NL: If blue(V1, V3, V4) is true and brown(V0, V1, V2) is explicitly false and red(V0, V3, V4) is true, then radio(V0, V2, V4) is explicitly false.
-radio(V0, V2, V4) :- blue(V1, V3, V4), -brown(V0, V1, V2), red(V0, V3, V4).
% Rule: r_70cc6f5aef42  |  line_index: 20  |  NL: If sanguine(V1, V4) is explicitly false and turkey_red(V2, V3) is explicitly false and scarlet(V0, V2, V3) is explicitly false and there is no evidence that army(V0, V2, V4) is true and there is no evidence that radio(V0, V2, V4) is explicitly false, then red(V0, V3, V4) is explicitly false.
-red(V0, V3, V4) :- -sanguine(V1, V4), -turkey_red(V2, V3), -scarlet(V0, V2, V3), not army(V0, V2, V4), not -radio(V0, V2, V4), person(V0).
% Rule: r_60da15146151  |  line_index: 21  |  NL: If school_cafeteria(V0, V1, V4) is explicitly false and lens(V1, V2, V3) is true, then students_to_socialize_in(V0, V2, V4) is explicitly false.
-students_to_socialize_in(V0, V2, V4) :- -school_cafeteria(V0, V1, V4), lens(V1, V2, V3).
% Rule: r_fc4c6b8a016f  |  line_index: 22  |  NL: If chromatic_color(V3) is explicitly false, then blue(V3, V3, V3) is true.
blue(V3, V3, V3) :- -chromatic_color(V3).
% Rule: r_0c08e66e428b  |  line_index: 23  |  NL: If light_brown(V0, V1, V2) is true, then brown(V0, V1, V2) is true.
brown(V0, V1, V2) :- light_brown(V0, V1, V2).
% Rule: r_d79b4d508c77  |  line_index: 24  |  NL: If yellow(V1, V3, V4) is true and there is no evidence that blue(V1, V3, V4) is true, then chromatic_color(V3) is true.
chromatic_color(V3) :- yellow(V1, V3, V4), not blue(V1, V3, V4).
% Rule: r_8c380534d8b0  |  line_index: 25  |  NL: If sheep(V1, V2) is explicitly false and there is no evidence that wool(V0, Pel1, V3) is explicitly false and gentle(V0, V2, V4) is true and there is no evidence that cotton(V0, V2, V4) is true and spring(V0, V3, V4) is explicitly false, then lambs(V2, V3, V4) is true.
lambs(V2, V3, V4) :- -sheep(V1, V2), not -wool(V0, Pel1, V3), gentle(V0, V2, V4), not cotton(V0, V2, V4), -spring(V0, V3, V4), person(V0), person(Pel1).
% Rule: r_f3bed66659d1  |  line_index: 26  |  NL: If brown(V0, V1, V2) is explicitly false, then red(V0, V1, V1) is true.
red(V0, V1, V1) :- -brown(V0, V1, V2).
% Rule: r_a0ca61fd0715  |  line_index: 27  |  NL: If yellow(V1, V3, V4) is explicitly false and there is no evidence that brown(V0, V1, V2) is true and red(V0, V3, V4) is true and redtail(V0, V1, V2) is true, then sanguine(V1, V4) is true.
sanguine(V1, V4) :- -yellow(V1, V3, V4), not brown(V0, V1, V2), red(V0, V3, V4), redtail(V0, V1, V2).
% Rule: r_b0c25611a494  |  line_index: 28  |  NL: If yellow(V1, V3, V4) is explicitly false and chromatic_color(V3) is explicitly false, then turkey_red(V4, V3) is true.
turkey_red(V4, V3) :- -yellow(V1, V3, V4), -chromatic_color(V3).
% Rule: r_d2744e94fa46  |  line_index: 29  |  NL: If blue(V1, V3, V4) is explicitly false and there is no evidence that canary_yellow(V1, V3, V4) is true, then yellow(V1, V3, V4) is true.
yellow(V1, V3, V4) :- -blue(V1, V3, V4), not canary_yellow(V1, V3, V4).