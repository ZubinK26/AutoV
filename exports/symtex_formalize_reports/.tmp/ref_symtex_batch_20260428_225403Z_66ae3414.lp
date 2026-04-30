- adult("Christina").
- bass("Benjamin", "Christina").
- beryl("Joy", "Leonard").
- bureaucratic_procedure("Joy", "Christina").
- erectile_tissue("Leonard", "Christina").
- hong_kong_dollar("Joy").
- mother_of_pearl("Benjamin", "Joy").
- ninian("Leonard", "Christina").
- open_sesame("Leonard").
- sawdust_doll("Benjamin", "Leonard").
- skin("Christina").
- small_print("Joy", "Christina").
- smoke("Benjamin", "Joy").
- utensil("Joy", "Christina").
carbonado("Benjamin", "Joy").
coloring("Benjamin", "Joy").
dimension("Leonard", "Christina").
heating_element("Benjamin", "Joy").
kill("Benjamin", "Joy").
race("Joy", "Christina").
sing_songs("Benjamin", "Joy").
- acculturation(V1) :- connect_to_hallways(V0, V1).
- acculturation(V1) :- drinking_establishment(V1, V3), connect_to_hallways(V0, V1), - holding(V2, V3).
- coinage(V1, V0) :- - connect_to_hallways(V0, V1), not mother_of_pearl(V0, V1), not smoke(V0, V1).
- fishing_trip(V1) :- - hong_kong_dollar(V1), - sawdust_doll(V0, V2), - beryl(V1, V2), - erectile_tissue(V2, V3), - ninian(V2, V3).
- solleret(V1) :- - hand_luggage(V1, V2).
acculturation(V1) :- hand_luggage(V1, V2), warner(V1, V3), not -holding(V2, V3).
cinnamon_bread(V1) :- - adult(V3), kill(V0, V1), not bass(V0, V3).
connect_to_hallways(V3, V1) :- not warner(V1, V3), not central_america(V1, V3), - bureaucratic_procedure(V1, V3).
hand_luggage(V1, V2) | - drinking_establishment(V1, V3) | solleret(V3) | - connect_to_hallways(V0, V1) :- - open_sesame(V2), - skin(V3), coloring(V0, V1), not -race(V1, V3), not -dimension(V2, V3).
holding(V3, V3) | central_america(V3, V3) :- solleret(V3).
mother_of_pearl(V0, V1) :- not -connect_to_hallways(V0, V1), - warner(V1, V3), not -heating_element(V0, V1), sing_songs(V0, V1), carbonado(V0, V1).
open_sesame(V0) :- connect_to_hallways(V0, V1).
open_sesame(V1) :- - acculturation(V1).
open_sesame(V2) :- - holding(V2, V3), not central_america(V1, V3), - acculturation(V1).
warner(V1, V3) :- - drinking_establishment(V1, V3), not -central_america(V1, V3), not coinage(V1, V3), not small_print(V1, V3), not utensil(V1, V3).