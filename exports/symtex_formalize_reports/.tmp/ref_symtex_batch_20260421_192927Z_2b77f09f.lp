- anyone("Alan", "Elizabeth", "Kristina").
- bruin("Alan", "Elizabeth", "Mark").
- dais("Alan").
- eat_meat("Alan").
- entering_building("Alan").
- measure("Alan", "Mark").
- priest("Theresa", "Elizabeth", "Kristina").
- profit("Alan").
- sao_goncalo("Alan", "Elizabeth", "Kristina").
- yak_butter("Theresa", "Alan", "Kristina").
carancha("Theresa", "Alan").
flank("Theresa", "Elizabeth", "Kristina").
object("Theresa", "Alan").
pancreas("Theresa", "Alan").
- coming_back_home(V0, V0) :- - kids(V0, V2, V4).
- head(V0, V1) | - kids(V0, V2, V4) | - zebra(V1, V4) | - waiter(V0, V4) :- - eat_meat(V1), - yak_butter(V0, V1, V3), flank(V0, V2, V3), - priest(V0, V2, V3), - bruin(V1, V2, V4).
- jackdaw(V3, V1) :- - coming_back_home(V1, V3), not dais(V1).
- liberian_dollar(V0, V1, V0) :- mailer(V0, V1), not jackdaw(V0, V1), not -object(V0, V1), not -pancreas(V0, V1), not -carancha(V0, V1).
- linoleum(V4, V2, V4) | character(V2, V2, V0) :- - waiter(V0, V4), having_to_eat(V0, V2).
gleaner(V1, V1) | mailer(V1, V1) | bittersweet_chocolate(V1, V1, V1) :- - eat_meat(V1), not entering_building(V1), not dais(V1), not profit(V1).
having_to_eat(V1, V4) :- - zebra(V1, V4), not measure(V1, V4).
row_of_bricks(V4, V2, V3) :- bittersweet_chocolate(V1, V2, V3), character(V1, V2, V3), - sao_goncalo(V1, V2, V3), - measure(V1, V4), not anyone(V1, V2, V3).
two_wheeled_vehicles(V4) :- - head(V0, V1), gleaner(V3, V4), - liberian_dollar(V0, V1, V2), not -row_of_bricks(V0, V2, V3), not linoleum(V1, V2, V4).