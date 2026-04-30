% NL: Suppose red's first move at turn 1 is (row 3, col 3), and blue plays optimally to prevent red
% from winning. Is there still a sequence where red wins by turn 25?
%
% Formalization (partial): constrain turn 1 to occurs(place(red,3,3),1). Require wins(red,T) for some T<=25.
% The policy does NOT encode "optimal blue"; optimality cannot be expressed without extra theory.
% This query answers: given red opens center, does ANY legal game exist where red wins by turn 25?

#show witness/0.

:- not occurs(place(red, 3, 3), 1).

witness :- wins(red, T), time(T), T >= 1, T <= 25.

:- not witness.
