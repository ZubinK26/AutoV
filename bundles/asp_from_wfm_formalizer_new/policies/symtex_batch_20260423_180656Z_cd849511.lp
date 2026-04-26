% Bundle: symtex_batch_20260423_180656Z_cd849511

% Rule: r_de2fbc0f5737  |  line_index: 0  |  NL: Jeremy is not beef.
-beef(jeremy).

% Rule: r_d8ad5b0ecd57  |  line_index: 1  |  NL: The cut is explicitly false.
-cut.

% Rule: r_d2c1beb8c398  |  line_index: 2  |  NL: Joel is not a gun enclosure.
-gun_enclosure(joel).

% Rule: r_6a7ae85612e5  |  line_index: 3  |  NL: The hawk is explicitly false.
-hawk.

% Rule: r_e3d8427a5db7  |  line_index: 4  |  NL: Joel is not an integer.
-integer(joel).

% Rule: r_f8a8f491ed00  |  line_index: 5  |  NL: Joel is not sad.
-sad(joel).

% Rule: r_21e713763b2a  |  line_index: 6  |  NL: Joel is not a semi-detached house.
-semi_detached_house(joel).

% Rule: r_b763e31d524b  |  line_index: 7  |  NL: Joel is an auxiliary engine.
auxiliary_engine(joel).

% Rule: r_99e51ccfb382  |  line_index: 8  |  NL: The beard is true.
beard.

% Rule: r_da06fe1b8d39  |  line_index: 9  |  NL: Joel is a berber.
berber(joel).

% Rule: r_24da7d93ee7b  |  line_index: 10  |  NL: Jeremy is a block.
block(jeremy).

% Rule: r_b75390e646a0  |  line_index: 11  |  NL: Joel is a calabar bean.
calabar_bean(joel).

% Rule: r_50e8caf61d51  |  line_index: 12  |  NL: Joel is computers.
computers(joel).

% Rule: r_8835e862d2c1  |  line_index: 13  |  NL: Joel is a norse deity.
norse_deity(joel).

% Rule: r_50b7c0053972  |  line_index: 14  |  NL: Joel is a papal cross.
papal_cross(joel).

% Rule: r_352e475423b8  |  line_index: 15  |  NL: Joel is a stratum granulosum.
stratum_granulosum(joel).

% Rule: r_938945524136  |  line_index: 16  |  NL: If V1 is not beef, then V1 is not an australian freeway.
-australian_freeway(V1) :- -beef(V1).

% Rule: r_ddf5d161d0ac  |  line_index: 17  |  NL: If there is no evidence that V0 is a steer and V0 is eating meals together, then V0 is not a beast.
-beast(V0) :- not steer(V0), eating_meals_together(V0).

% Rule: r_a84c6cc1dbd9  |  line_index: 18  |  NL: If V0 is not a domestic fowl, then V0 is not a binder.
-binder(V0) :- -domestic_fowl(V0).

% Rule: r_3c3987d08a95  |  line_index: 19  |  NL: If V1 is a block, then V1 is not a board.
-board(V1) :- block(V1).

% Rule: r_f121addb93ab  |  line_index: 20  |  NL: If V0 is a fragment and there is no evidence that V0 is a gun enclosure, then V0 is not a domestic fowl.
-domestic_fowl(V0) :- fragment(V0), not gun_enclosure(V0).

% Rule: r_f2f2dba66834  |  line_index: 21  |  NL: If V0 is not a binder and there is no evidence that V0 is not a steer and there is no evidence that V0 is not a beast, then V0 is not eating meals together.
-eating_meals_together(V0) :- -binder(V0), not -steer(V0), not -beast(V0).

% Rule: r_8e1f582047b4  |  line_index: 22  |  NL: If V0 is a binder and V0 is not feed babies and there is no evidence that V0 is not a papal cross, then V0 is not a fragment.
-fragment(V0) :- binder(V0), -feed_babies(V0), not -papal_cross(V0).

% Rule: r_e5ce62d840e0  |  line_index: 23  |  NL: If V1 is a board and there is no evidence that V0 is a steer and V0 is not feed babies, then V0 is not a fragment.
-fragment(V0) :- board(V1), not steer(V0), -feed_babies(V0).

% Rule: r_950fbbd059f7  |  line_index: 24  |  NL: If V0 is eating meals together, then V0 is not a fragment.
-fragment(V0) :- eating_meals_together(V0).

% Rule: r_fd5ddca0e341  |  line_index: 25  |  NL: If V0 is feed babies, then V0 is a beast.
beast(V0) :- feed_babies(V0).

% Rule: r_084c28a98c6b  |  line_index: 26  |  NL: If V1 is a board and there is no evidence that V0 is a steer and V0 is not feed babies, then V0 is a binder.
binder(V0) :- board(V1), not steer(V0), -feed_babies(V0).

% Rule: r_79604189588c  |  line_index: 27  |  NL: If V0 is not a beast and the beard is true, then V0 is a board.
board(V0) :- -beast(V0), beard.

% Rule: r_bb8276297937  |  line_index: 28  |  NL: If V0 is not a beast and there is no evidence that V0 is feed babies, then V0 is eating meals together.
eating_meals_together(V0) :- -beast(V0), not feed_babies(V0).

% Rule: r_7dd7d4d44f47  |  line_index: 29  |  NL: If there is no evidence that V0 is not a binder and V0 is not a steer and there is no evidence that V0 is feed babies, then V0 is eating meals together.
eating_meals_together(V0) :- not -binder(V0), -steer(V0), not feed_babies(V0).

% Rule: r_e1fbc4035bce  |  line_index: 30  |  NL: If V0 is a stratum granulosum and there is no evidence that V0 is a semi-detached house and there is no evidence that V0 is a gun enclosure, then V0 is feed babies.
feed_babies(V0) :- stratum_granulosum(V0), not semi_detached_house(V0), not gun_enclosure(V0).

% Rule: r_093c93ea6f33  |  line_index: 31  |  NL: If V0 is an invasion and there is no evidence that V0 is an integer and there is no evidence that V0 is not a berber, then V0 is a fragment.
fragment(V0) :- invasion(V0), not integer(V0), not -berber(V0).

% Rule: r_468bf9c7bbec  |  line_index: 32  |  NL: If V1 is not a board and there is no evidence that the cut is true and there is no evidence that the hawk is true, then V1 is an invasion.
invasion(V1) :- -board(V1), not cut, not hawk.

% Rule: r_32564a871e83  |  line_index: 33  |  NL: If V0 is an auxiliary engine and V0 is not sad, then V0 is launch space shuttle into orbit.
launch_space_shuttle_into_orbit(V0) :- auxiliary_engine(V0), -sad(V0).

% Rule: r_a24a25cf45c5  |  line_index: 34  |  NL: If V0 is computers and there is no evidence that V0 is not a calabar bean and there is no evidence that V0 is not a norse deity, then V0 is a steer.
steer(V0) :- computers(V0), not -calabar_bean(V0), not -norse_deity(V0).