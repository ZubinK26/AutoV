% NL: Is there a sequence of legal moves on a 5x5 Hex board where the red player wins by turn 25?
%
% Formalization: some turn T with 1 <= T <= 25 such that wins(red, T).

#show witness_win_turn/1.

witness_win_turn(T) :- wins(red, T), time(T), T >= 1, T <= 25.

has_witness :- witness_win_turn(_).

:- not has_witness.
