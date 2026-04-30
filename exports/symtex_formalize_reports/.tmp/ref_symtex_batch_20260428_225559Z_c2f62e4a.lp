- army("Kevin", "Jenny", "Katelyn").
- canary_yellow("Alexander", "Mariah", "Katelyn").
- cotton("Kevin", "Jenny", "Katelyn").
- sanguine("Alexander", "Katelyn").
- scarlet("Kevin", "Jenny", "Mariah").
- school_cafeteria("Kevin", "Alexander", "Katelyn").
- sheep("Alexander", "Jenny").
- spring("Kevin", "Mariah", "Katelyn").
- turkey_red("Jenny", "Mariah").
gentle("Kevin", "Jenny", "Katelyn").
lens("Alexander", "Jenny", "Mariah").
light_brown("Kevin", "Alexander", "Jenny").
radio("Kevin", "Jenny", "Katelyn").
redtail("Kevin", "Alexander", "Jenny").
wool("Kevin", "Alexander", "Mariah").
- blue(V1, V3, V4) :- brown(V0, V1, V2), - red(V0, V3, V4).
- chromatic_color(V3) :- - yellow(V1, V3, V4), blue(V1, V3, V4), - brown(V0, V1, V2), not -red(V0, V3, V4).
- chromatic_color(V3) :- - yellow(V1, V3, V4), not -blue(V1, V3, V4).
- light_brown(V0, V1, V2) :- - yellow(V1, V3, V4), - brown(V0, V1, V2), not -red(V0, V3, V4).
- radio(V0, V2, V4) :- blue(V1, V3, V4), - brown(V0, V1, V2), red(V0, V3, V4).
- red(V0, V3, V4) :- - sanguine(V1, V4), - turkey_red(V2, V3), - scarlet(V0, V2, V3), not army(V0, V2, V4), not -radio(V0, V2, V4).
- students_to_socialize_in(V0, V2, V4) :- - school_cafeteria(V0, V1, V4), lens(V1, V2, V3).
blue(V3, V3, V3) :- - chromatic_color(V3).
brown(V0, V1, V2) :- light_brown(V0, V1, V2).
chromatic_color(V3) :- yellow(V1, V3, V4), not blue(V1, V3, V4).
lambs(V2, V3, V4) :- - sheep(V1, V2), not -wool(V0, V1, V3), gentle(V0, V2, V4), not cotton(V0, V2, V4), - spring(V0, V3, V4).
red(V0, V1, V1) :- - brown(V0, V1, V2).
sanguine(V1, V4) :- - yellow(V1, V3, V4), not brown(V0, V1, V2), red(V0, V3, V4), redtail(V0, V1, V2).
turkey_red(V4, V3) :- - yellow(V1, V3, V4), - chromatic_color(V3).
yellow(V1, V3, V4) :- - blue(V1, V3, V4), not canary_yellow(V1, V3, V4).