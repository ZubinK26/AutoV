% Bundle: nlchunk_20260426_223352Z_427e854a
% Rule: r_2e2dbfb32525  |  line_index: 0  |  NL: There is exactly one board.
board(b1).
:- board(B1), board(B2), B1 != B2.
:- not board(b1).

% Rule: r_83afcbe49b56  |  line_index: 4  |  NL: Rows are numbered 1 through 5.
row(1..5).

% Rule: r_9cd54eb073bc  |  line_index: 5  |  NL: Columns are numbered 1 through 5.
column(1..5).

% Rule: r_617fd2ece980  |  line_index: 1  |  NL: The board contains exactly twenty-five cells.
% Rule: r_c87ec002623b  |  line_index: 2  |  NL: Every cell is identified by exactly one row.
% Rule: r_c458c438da51  |  line_index: 3  |  NL: Every cell is identified by exactly one column.
% Rule: r_701dcc920618  |  line_index: 6  |  NL: Every cell is identified by exactly one pair (R, C).
% Rule: r_bc856e4f2d9e  |  line_index: 7  |  NL: R is the row number.
% Rule: r_4ddff7dd2df9  |  line_index: 8  |  NL: C is the column number.
cell(R, C) :- row(R), column(C).
:- not { cell(R, C) } = 25.

% Rule: r_fb93253e4e4a  |  line_index: 9  |  NL: The board has exactly four edges.
% Rule: r_4e72bdc22740  |  line_index: 10  |  NL: The edges are the top edge, the bottom edge, the left edge, and the right edge.
edge(top).
edge(bottom).
edge(left).
edge(right).
:- not { edge(E) } = 4.

% Rule: r_3825f3621c2d  |  line_index: 11  |  NL: Every cell in row 1 is located on the top edge.
located_on(1, C, top) :- cell(1, C).

% Rule: r_30373a2a8887  |  line_index: 12  |  NL: Every cell in row 5 is located on the bottom edge.
located_on(5, C, bottom) :- cell(5, C).

% Rule: r_9e3d38bfb9bb  |  line_index: 13  |  NL: Every cell in column 1 is located on the left edge.
located_on(R, 1, left) :- cell(R, 1).

% Rule: r_a5229a113c21  |  line_index: 14  |  NL: Every cell in column 5 is located on the right edge.
located_on(R, 5, right) :- cell(R, 5).

% Rule: r_0f89c29c19ac  |  line_index: 15  |  NL: There are exactly two players.
% Rule: r_4c8334b55c47  |  line_index: 16  |  NL: The players are the red player and the blue player.
player(red).
player(blue).
:- not { player(P) } = 2.

% Rule: r_0b4bb43a6245  |  line_index: 17  |  NL: The red player is assigned the top edge.
assigned(red, top).

% Rule: r_125a85ab7493  |  line_index: 18  |  NL: The red player is assigned the bottom edge.
assigned(red, bottom).