% NL: Is there a sequence of legal moves on a 5x5 Hex board where the blue player wins by turn 25?
%
% Formalization: some turn T with 1 <= T <= 25 such that wins(blue, T).

#show witness_win_turn/1.

witness_win_turn(T) :- wins(blue, T), time(T), T >= 1, T <= 25.

has_witness :- witness_win_turn(_).

:- not has_witness.
