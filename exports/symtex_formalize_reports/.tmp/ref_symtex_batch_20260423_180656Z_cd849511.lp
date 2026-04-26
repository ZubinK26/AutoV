- beef("Jeremy").
- cut.
- gun_enclosure("Joel").
- hawk.
- integer("Joel").
- sad("Joel").
- semi_detached_house("Joel").
auxiliary_engine("Joel").
beard.
berber("Joel").
block("Jeremy").
calabar_bean("Joel").
computers("Joel").
norse_deity("Joel").
papal_cross("Joel").
stratum_granulosum("Joel").
- australian_freeway(V1) :- - beef(V1).
- beast(V0) :- not steer(V0), eating_meals_together(V0).
- binder(V0) :- - domestic_fowl(V0).
- board(V1) :- block(V1).
- domestic_fowl(V0) :- fragment(V0), not gun_enclosure(V0).
- eating_meals_together(V0) :- - binder(V0), not -steer(V0), not -beast(V0).
- fragment(V0) :- binder(V0), - feed_babies(V0), not -papal_cross(V0).
- fragment(V0) :- board(V1), not steer(V0), - feed_babies(V0).
- fragment(V0) :- eating_meals_together(V0).
beast(V0) :- feed_babies(V0).
binder(V0) :- board(V1), not steer(V0), - feed_babies(V0).
board(V0) :- - beast(V0), beard.
eating_meals_together(V0) :- - beast(V0), not feed_babies(V0).
eating_meals_together(V0) :- not -binder(V0), - steer(V0), not feed_babies(V0).
feed_babies(V0) :- stratum_granulosum(V0), not semi_detached_house(V0), not gun_enclosure(V0).
fragment(V0) :- invasion(V0), not integer(V0), not -berber(V0).
invasion(V1) :- - board(V1), not cut, not hawk.
launch_space_shuttle_into_orbit(V0) :- auxiliary_engine(V0), - sad(V0).
steer(V0) :- computers(V0), not -calabar_bean(V0), not -norse_deity(V0).