% Bundle: symtex_batch_20260423_180656Z_cd849511

% Rule: r_5b74e8e93a88  |  line_index: 0  |  NL: Jeremy is not beef.
-beef(jeremy).

% Rule: r_b25e24919119  |  line_index: 1  |  NL: The cut is explicitly false.
-cut.

% Rule: r_b9925321723d  |  line_index: 2  |  NL: Joel is not a gun enclosure.
-gun_enclosure(joel).

% Rule: r_b61d2a079968  |  line_index: 3  |  NL: The hawk is explicitly false.
-hawk.

% Rule: r_77823d4bbecd  |  line_index: 4  |  NL: Joel is not an integer.
-integer(joel).

% Rule: r_2ef881a8d3bf  |  line_index: 5  |  NL: Joel is not sad.
-sad(joel).

% Rule: r_9b52ac2a0350  |  line_index: 6  |  NL: Joel is not a semi-detached house.
-semi_detached_house(joel).

% Rule: r_4b898f3ec2cd  |  line_index: 7  |  NL: Joel is an auxiliary engine.
auxiliary_engine(joel).

% Rule: r_78dcbec8f248  |  line_index: 8  |  NL: The beard is true.
beard.

% Rule: r_9e0f4dfc2c67  |  line_index: 9  |  NL: Joel is a berber.
berber(joel).

% Rule: r_9eb64c4cf2b4  |  line_index: 10  |  NL: Jeremy is a block.
block(jeremy).

% Rule: r_210eed18d373  |  line_index: 11  |  NL: Joel is a calabar bean.
calabar_bean(joel).

% Rule: r_cdf12dfd43dd  |  line_index: 12  |  NL: Joel is computers.
computers(joel).

% Rule: r_046e7b575420  |  line_index: 13  |  NL: Joel is a norse deity.
norse_deity(joel).

% Rule: r_4685058defe8  |  line_index: 14  |  NL: Joel is a papal cross.
papal_cross(joel).

% Rule: r_0aa505fe2a8d  |  line_index: 15  |  NL: Joel is a stratum granulosum.
stratum_granulosum(joel).

% Rule: r_666c1a730705  |  line_index: 16  |  NL: If V1 is not beef, then V1 is not an australian freeway.
-australian_freeway(V1) :- -beef(V1), entity(V1).

% Rule: r_d54b90750459  |  line_index: 17  |  NL: If there is no evidence that V0 is a steer and V0 is eating meals together, then V0 is not a beast.
-beast(V0) :- not steer(V0), eating_meals_together(V0), entity(V0).

% Rule: r_5e5bb091a70c  |  line_index: 18  |  NL: If V0 is not a domestic fowl, then V0 is not a binder.
-binder(V0) :- -domestic_fowl(V0), entity(V0).

% Rule: r_8c06b39875fa  |  line_index: 19  |  NL: If V1 is a block, then V1 is not a board.
-board(V1) :- block(V1), entity(V1).

% Rule: r_32c425a25738  |  line_index: 20  |  NL: If V0 is a fragment and there is no evidence that V0 is a gun enclosure, then V0 is not a domestic fowl.
-domestic_fowl(V0) :- fragment(V0), not gun_enclosure(V0), entity(V0).

% Rule: r_9fb50ad19b8a  |  line_index: 21  |  NL: If V0 is not a binder and there is no evidence that V0 is not a steer and there is no evidence that V0 is not a beast, then V0 is not eating meals together.
-eating_meals_together(V0) :- -binder(V0), not -steer(V0), not -beast(V0), entity(V0).

% Rule: r_99d767783d2e  |  line_index: 22  |  NL: If V0 is a binder and V0 is not feed babies and there is no evidence that V0 is not a papal cross, then V0 is not a fragment.
-fragment(V0) :- binder(V0), -feed_babies(V0), not -papal_cross(V0), entity(V0).

% Rule: r_f49e0cd0191b  |  line_index: 23  |  NL: If V1 is a board and there is no evidence that V0 is a steer and V0 is not feed babies, then V0 is not a fragment.
-fragment(V0) :- board(V1), not steer(V0), -feed_babies(V0), entity(V0), entity(V1).

% Rule: r_7bd0af396f52  |  line_index: 24  |  NL: If V0 is eating meals together, then V0 is not a fragment.
-fragment(V0) :- eating_meals_together(V0), entity(V0).

% Rule: r_5ff59eff4fd9  |  line_index: 25  |  NL: If V0 is feed babies, then V0 is a beast.
beast(V0) :- feed_babies(V0), entity(V0).

% Rule: r_f2ecd2bfb6f0  |  line_index: 26  |  NL: If V1 is a board and there is no evidence that V0 is a steer and V0 is not feed babies, then V0 is a binder.
binder(V0) :- board(V1), not steer(V0), -feed_babies(V0), entity(V0), entity(V1).

% Rule: r_60c751eebef6  |  line_index: 27  |  NL: If V0 is not a beast and the beard is true, then V0 is a board.
board(V0) :- -beast(V0), beard, entity(V0).

% Rule: r_a268d108da96  |  line_index: 28  |  NL: If V0 is not a beast and there is no evidence that V0 is feed babies, then V0 is eating meals together.
eating_meals_together(V0) :- -beast(V0), not feed_babies(V0), entity(V0).

% Rule: r_e7506361c991  |  line_index: 29  |  NL: If there is no evidence that V0 is not a binder and V0 is not a steer and there is no evidence that V0 is feed babies, then V0 is eating meals together.
eating_meals_together(V0) :- not -binder(V0), -steer(V0), not feed_babies(V0), entity(V0).

% Rule: r_ae835cbc82b9  |  line_index: 30  |  NL: If V0 is a stratum granulosum and there is no evidence that V0 is a semi-detached house and there is no evidence that V0 is a gun enclosure, then V0 is feed babies.
feed_babies(V0) :- stratum_granulosum(V0), not semi_detached_house(V0), not gun_enclosure(V0), entity(V0).

% Rule: r_2d16cb46c77f  |  line_index: 31  |  NL: If V0 is an invasion and there is no evidence that V0 is an integer and there is no evidence that V0 is not a berber, then V0 is a fragment.
fragment(V0) :- invasion(V0), not integer(V0), not -berber(V0), entity(V0).

% Rule: r_1b42e0da945d  |  line_index: 32  |  NL: If V1 is not a board and there is no evidence that the cut is true and there is no evidence that the hawk is true, then V1 is an invasion.
invasion(V1) :- -board(V1), not cut, not hawk, entity(V1).

% Rule: r_2e3b4ccb4159  |  line_index: 33  |  NL: If V0 is an auxiliary engine and V0 is not sad, then V0 is launch space shuttle into orbit.
launch_space_shuttle_into_orbit(V0) :- auxiliary_engine(V0), -sad(V0), entity(V0).

% Rule: r_13bd457a6230  |  line_index: 34  |  NL: If V0 is computers and there is no evidence that V0 is not a calabar bean and there is no evidence that V0 is not a norse deity, then V0 is a steer.
steer(V0) :- computers(V0), not -calabar_bean(V0), not -norse_deity(V0), entity(V0).

entity(jeremy).
entity(joel).