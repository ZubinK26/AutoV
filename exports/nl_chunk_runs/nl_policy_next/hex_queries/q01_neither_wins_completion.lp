% NL: Is there a sequence of legal moves on a 5x5 Hex board, played to completion (turn 25),
% where neither the red player nor the blue player has won?
%
% Formalization: require that no player wins at any turn T with 1 <= T <= 25 (same turn domain as policy).
% "Played to completion (turn 25)" is already forced by the policy (full schedule of moves through time 25).

#show witness/0.

witness :- not any_win_by_25.

any_win_by_25 :- wins(P, T), player(P), time(T), T >= 1, T <= 25.

:- not witness.
