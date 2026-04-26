- chick("Aaron", "Kimberly").
- exodus("Richard", "Aaron").
- mist("Richard", "Kimberly").
- playing_harp("Kimberly", "Daniel").
- protection("Aaron", "Kimberly").
- riding_boot("Kimberly", "Daniel").
- room("Kimberly", "Daniel").
- summer("Richard", "Daniel").
bakery("Richard", "Aaron").
cold("Daniel").
creation("Richard", "Aaron").
drop("Aaron", "Kimberly").
garment_cutter("Richard", "Aaron").
heat("Daniel").
procedure("Kimberly", "Daniel").
soup("Aaron", "Daniel").
steam("Daniel").
- after(V1) :- - summer(V0, V3), - chick(V1, V2), not -soup(V1, V3).
- angels(V1) :- thunder(V1, V2), zebu(V1, V3), not playing_harp(V2, V3).
- dew(V0, V1) :- - mist(V0, V2), drop(V1, V2), - room(V2, V3).
- drop(V1, V0) :- dew(V0, V1), - smoke(V1, V3), angels(V1).
- drop(V1, V3) :- hot(V3), after(V1), not -angels(V1).
- hot(V3) :- - summer(V0, V3), - chick(V1, V2), not -soup(V1, V3).
- morning(V1, V1) :- dew(V0, V1), not -bakery(V0, V1).
- temperature(V3, V3) :- - hot(V3), not -heat(V3), not -cold(V3).
- thunder(V3, V3) :- hot(V3).
activity(V1, V3) :- creation(V0, V1), - protection(V1, V2), procedure(V2, V3).
after(V1) :- - thunder(V1, V2), temperature(V0, V3), - morning(V1, V3).
angels(V1) :- - fire(V1, V3), not -hot(V3), temperature(V0, V3).
angels(V3) :- hot(V3).
boot(V2, V3) :- - riding_boot(V2, V3).
escape(V0, V1) :- - exodus(V0, V1).
fire(V1, V3) :- - hot(V3), - temperature(V0, V3), smoke(V1, V3).
hot(V3) :- - fire(V1, V3), after(V1), temperature(V0, V3).
morning(V1, V1) :- - dew(V0, V1), not after(V1), not -garment_cutter(V0, V1).
smoke(V3, V3) :- - hot(V3), not -steam(V3).
thunder(V1, V2) :- creation(V0, V1), - protection(V1, V2), procedure(V2, V3).
zebu(V1, V3) :- activity(V1, V3), not -fire(V1, V3), not -morning(V1, V3).