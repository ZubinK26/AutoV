- yellowbelly_marmot("Mary", "Sabrina").
- bovine("Mary", "Alison", "Cynthia").
- horn("Mary", "Sabrina", "Anthony").
bullock("Mary", "Cynthia", "Anthony").
hoary_marmot("Sabrina", "Cynthia").
- sight_organ("Mary", "Alison", "Sabrina").
- squirrel("Sabrina", "Anthony").
- abrocome("Cynthia", "Anthony").
cattle(V0, V2, V3) :- - placental(V0, V2, V3).
rodent(V0, V3, V4) :- marmot(V0, V3), - squirrel(V2, V4), not abrocome(V3, V4).
marmot(V0, V3) :- - yellowbelly_marmot(V0, V2), hoary_marmot(V2, V3), - sight_organ(V0, V1, V2).
- bull(V0, V1, V2) :- - bovine(V0, V1, V3), - horn(V0, V2, V4), not -bullock(V0, V3, V4).
- udder(V0, V3, V4) :- - bovine(V0, V1, V3), - horn(V0, V2, V4), not -bullock(V0, V3, V4).
- placental(V0, V2, V3) :- rodent(V0, V3, V4), - bull(V0, V1, V2), not cow(V0, V1, V2).
- cow(V0, V0, V4) :- rodent(V0, V3, V4), not udder(V0, V3, V4).