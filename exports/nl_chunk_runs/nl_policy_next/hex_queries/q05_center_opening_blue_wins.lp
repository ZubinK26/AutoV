% Q5 (revised) — symmetry-broken "blue wins after red center opening"
%
% English: Red's first move at turn 1 is (3,3). Blue's first move at turn 2 is in the upper-left
% 3×3 block (row<=3, column<=3), excluding the center (already red). Blue wins by turn 25 (left–right
% chain — as in policy wins(blue,T)).
%
% Soundness sketch: With red fixed at center, the empty board has dihedral symmetry fixing the center;
% any winning play where blue's first stone is outside that quadrant maps by symmetry to one with
% blue's first move in row<=3 & col<=3 \ {(3,3)}, so ∃-SAT is preserved under this restriction.
%
% Policy predicates only: occurs/3, wins/2, time/1.

#show witness/0.

:- not occurs(place(red, 3, 3), 1).

% Blue's first move (turn 2): narrow to the 8 cells in upper-left quadrant minus center
:- occurs(place(blue, R, C), 2), R > 3.
:- occurs(place(blue, R, C), 2), C > 3.
:- occurs(place(blue, 3, 3), 2).

witness :- wins(blue, T), time(T), T >= 1, T <= 25.

:- not witness.
