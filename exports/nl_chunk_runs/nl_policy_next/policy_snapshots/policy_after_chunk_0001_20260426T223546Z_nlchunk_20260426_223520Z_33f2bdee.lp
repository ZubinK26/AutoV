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

% Bundle: nlchunk_20260426_223445Z_55a8ff0a
% Rule: r_b9049ad496fb  |  line_index: 0  |  NL: There is exactly one board.
board(b1).
:- board(B1), board(B2), B1 != B2.
:- not board(b1).

% Rule: r_a9570bf7dea0  |  line_index: 4  |  NL: Rows are numbered 1, 2, 3, 4, and 5.
row(1..5).

% Rule: r_2e1ba7a39379  |  line_index: 5  |  NL: Columns are numbered 1, 2, 3, 4, and 5.
column(1..5).

% Rule: r_0b2c73e94c84  |  line_index: 1  |  NL: The board contains exactly twenty-five cells.
% Rule: r_048e6d4d30de  |  line_index: 2  |  NL: Every cell is identified by exactly one row.
% Rule: r_9ad4e4a4418d  |  line_index: 3  |  NL: Every cell is identified by exactly one column.
% Rule: r_f0e4d9bf2bc6  |  line_index: 6  |  NL: Every cell is identified by exactly one pair (R, C), where R is the row of the cell and C is the column of the cell.
cell(R, C) :- row(R), column(C).
:- not { cell(R, C) } = 25.

% Rule: r_614c079a285f  |  line_index: 7  |  NL: The board has exactly four edges.
% Rule: r_2077e4f436ea  |  line_index: 8  |  NL: The edges are the top edge, the bottom edge, the left edge, and the right edge.
edge(top).
edge(bottom).
edge(left).
edge(right).
:- not { edge(E) } = 4.

% Rule: r_6032b5ce259d  |  line_index: 9  |  NL: Every cell in row 1 is located on the top edge.
located_on(1, C, top) :- cell(1, C).

% Rule: r_69aa94b04252  |  line_index: 10  |  NL: Every cell in row 5 is located on the bottom edge.
located_on(5, C, bottom) :- cell(5, C).

% Rule: r_07dbd6d6f274  |  line_index: 11  |  NL: Every cell in column 1 is located on the left edge.
located_on(R, 1, left) :- cell(R, 1).

% Rule: r_43b1d2a00446  |  line_index: 12  |  NL: Every cell in column 5 is located on the right edge.
located_on(R, 5, right) :- cell(R, 5).

% Rule: r_0112f2b1aa3f  |  line_index: 13  |  NL: There are exactly two players.
% Rule: r_61ca6b44d9f1  |  line_index: 14  |  NL: The players are the red player and the blue player.
player(red).
player(blue).
:- not { player(P) } = 2.

% Rule: r_ae3e556aaffa  |  line_index: 15  |  NL: The red player is assigned the top edge.
assigned(red, top).

% Rule: r_f6892401e9bb  |  line_index: 16  |  NL: The red player is assigned the bottom edge.
assigned(red, bottom).

% Bundle: nlchunk_20260426_223520Z_33f2bdee
% Rule: r_5b84c2c8ce79  |  line_index: 0  |  NL: The blue player is assigned the left edge.
assigned(blue, left).
% Rule: r_7b275741a0dc  |  line_index: 1  |  NL: The blue player is assigned the right edge.
assigned(blue, right).
% Rule: r_966aa857df00  |  line_index: 2  |  NL: The cell at row 1 and column 1 is adjacent to the cell at row 1 and column 2.
adjacent(1, 1, 1, 2).
% Rule: r_2975cdefe35e  |  line_index: 3  |  NL: The cell at row 1 and column 1 is adjacent to the cell at row 2 and column 1.
adjacent(1, 1, 2, 1).
% Rule: r_f5d9d8399467  |  line_index: 4  |  NL: The cell at row 1 and column 2 is adjacent to the cell at row 1 and column 3.
adjacent(1, 2, 1, 3).
% Rule: r_305706ac37ed  |  line_index: 5  |  NL: The cell at row 1 and column 2 is adjacent to the cell at row 2 and column 1.
adjacent(1, 2, 2, 1).
% Rule: r_f916fbfa1ba0  |  line_index: 6  |  NL: The cell at row 1 and column 2 is adjacent to the cell at row 2 and column 2.
adjacent(1, 2, 2, 2).
% Rule: r_703c7942a19c  |  line_index: 7  |  NL: The cell at row 1 and column 3 is adjacent to the cell at row 1 and column 4.
adjacent(1, 3, 1, 4).
% Rule: r_223b5fe0f11c  |  line_index: 8  |  NL: The cell at row 1 and column 3 is adjacent to the cell at row 2 and column 2.
adjacent(1, 3, 2, 2).
% Rule: r_6e258c2d6ab8  |  line_index: 9  |  NL: The cell at row 1 and column 3 is adjacent to the cell at row 2 and column 3.
adjacent(1, 3, 2, 3).
% Rule: r_34f10d136c59  |  line_index: 10  |  NL: The cell at row 1 and column 4 is adjacent to the cell at row 1 and column 5.
adjacent(1, 4, 1, 5).