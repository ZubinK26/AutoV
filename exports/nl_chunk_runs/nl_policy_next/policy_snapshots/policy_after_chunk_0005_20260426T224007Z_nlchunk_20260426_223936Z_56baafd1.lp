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

% Bundle: nlchunk_20260426_223553Z_d8f43d4e
% Rule: r_b7822ef23a1a  |  line_index: 0  |  NL: The cell at row 1 and column 4 is adjacent to the cell at row 2 and column 3.
adjacent(1, 4, 2, 3).
% Rule: r_12c6e9033761  |  line_index: 1  |  NL: The cell at row 1 and column 4 is adjacent to the cell at row 2 and column 4.
adjacent(1, 4, 2, 4).
% Rule: r_e1d56252db08  |  line_index: 2  |  NL: The cell at row 1 and column 5 is adjacent to the cell at row 2 and column 4.
adjacent(1, 5, 2, 4).
% Rule: r_b2900e7f40d6  |  line_index: 3  |  NL: The cell at row 1 and column 5 is adjacent to the cell at row 2 and column 5.
adjacent(1, 5, 2, 5).
% Rule: r_e613b56b1654  |  line_index: 4  |  NL: The cell at row 2 and column 1 is adjacent to the cell at row 2 and column 2.
adjacent(2, 1, 2, 2).
% Rule: r_ae694e0056c1  |  line_index: 5  |  NL: The cell at row 2 and column 1 is adjacent to the cell at row 3 and column 1.
adjacent(2, 1, 3, 1).
% Rule: r_992a4198e49a  |  line_index: 6  |  NL: The cell at row 2 and column 2 is adjacent to the cell at row 2 and column 3.
adjacent(2, 2, 2, 3).
% Rule: r_002433c8ee87  |  line_index: 7  |  NL: The cell at row 2 and column 2 is adjacent to the cell at row 3 and column 1.
adjacent(2, 2, 3, 1).
% Rule: r_7a24eb853436  |  line_index: 8  |  NL: The cell at row 2 and column 2 is adjacent to the cell at row 3 and column 2.
adjacent(2, 2, 3, 2).
% Rule: r_e6f72cfecd1b  |  line_index: 9  |  NL: The cell at row 2 and column 3 is adjacent to the cell at row 2 and column 4.
adjacent(2, 3, 2, 4).

% Bundle: nlchunk_20260426_223823Z_59a3b73b
% Rule: r_85f7a874ddf6  |  line_index: 0  |  NL: The cell at row 2 and column 3 is adjacent to the cell at row 3 and column 2.
adjacent(2, 3, 3, 2).
% Rule: r_b4afc1f8bc24  |  line_index: 1  |  NL: The cell at row 2 and column 3 is adjacent to the cell at row 3 and column 3.
adjacent(2, 3, 3, 3).
% Rule: r_e2ddb8e1c205  |  line_index: 2  |  NL: The cell at row 2 and column 4 is adjacent to the cell at row 2 and column 5.
adjacent(2, 4, 2, 5).
% Rule: r_bf161228ce9c  |  line_index: 3  |  NL: The cell at row 2 and column 4 is adjacent to the cell at row 3 and column 3.
adjacent(2, 4, 3, 3).
% Rule: r_e657b1fc1be0  |  line_index: 4  |  NL: The cell at row 2 and column 4 is adjacent to the cell at row 3 and column 4.
adjacent(2, 4, 3, 4).
% Rule: r_0e6af9e5ae7a  |  line_index: 5  |  NL: The cell at row 2 and column 5 is adjacent to the cell at row 3 and column 4.
adjacent(2, 5, 3, 4).
% Rule: r_2d7967db6a68  |  line_index: 6  |  NL: The cell at row 2 and column 5 is adjacent to the cell at row 3 and column 5.
adjacent(2, 5, 3, 5).
% Rule: r_a1a9d1d38646  |  line_index: 7  |  NL: The cell at row 3 and column 1 is adjacent to the cell at row 3 and column 2.
adjacent(3, 1, 3, 2).
% Rule: r_91a6dfc2d64a  |  line_index: 8  |  NL: The cell at row 3 and column 1 is adjacent to the cell at row 4 and column 1.
adjacent(3, 1, 4, 1).
% Rule: r_c2bcf72daa8d  |  line_index: 9  |  NL: The cell at row 3 and column 2 is adjacent to the cell at row 3 and column 3.
adjacent(3, 2, 3, 3).

% Bundle: nlchunk_20260426_223859Z_7211d376
% Rule: r_bbdcd3551fab  |  line_index: 0  |  NL: The cell at row 3 and column 2 is adjacent to the cell at row 4 and column 1.
adjacent(3, 2, 4, 1).
% Rule: r_62f2c18b92cd  |  line_index: 1  |  NL: The cell at row 3 and column 2 is adjacent to the cell at row 4 and column 2.
adjacent(3, 2, 4, 2).
% Rule: r_977d4f8b3bce  |  line_index: 2  |  NL: The cell at row 3 and column 3 is adjacent to the cell at row 3 and column 4.
adjacent(3, 3, 3, 4).
% Rule: r_807c126613e6  |  line_index: 3  |  NL: The cell at row 3 and column 3 is adjacent to the cell at row 4 and column 2.
adjacent(3, 3, 4, 2).
% Rule: r_d5de9109c1e5  |  line_index: 4  |  NL: The cell at row 3 and column 3 is adjacent to the cell at row 4 and column 3.
adjacent(3, 3, 4, 3).
% Rule: r_ffe3126ae971  |  line_index: 5  |  NL: The cell at row 3 and column 4 is adjacent to the cell at row 3 and column 5.
adjacent(3, 4, 3, 5).
% Rule: r_701d92306b2e  |  line_index: 6  |  NL: The cell at row 3 and column 4 is adjacent to the cell at row 4 and column 3.
adjacent(3, 4, 4, 3).
% Rule: r_7a57ba7df434  |  line_index: 7  |  NL: The cell at row 3 and column 4 is adjacent to the cell at row 4 and column 4.
adjacent(3, 4, 4, 4).
% Rule: r_32730edaa3a2  |  line_index: 8  |  NL: The cell at row 3 and column 5 is adjacent to the cell at row 4 and column 4.
adjacent(3, 5, 4, 4).
% Rule: r_c9b6391a315e  |  line_index: 9  |  NL: The cell at row 3 and column 5 is adjacent to the cell at row 4 and column 5.
adjacent(3, 5, 4, 5).

% Bundle: nlchunk_20260426_223936Z_56baafd1
% Rule: r_4849bd89d3b3  |  line_index: 0  |  NL: The cell at row 4 and column 1 is adjacent to the cell at row 4 and column 2.
adjacent(4, 1, 4, 2).
% Rule: r_84f0cffabbf0  |  line_index: 1  |  NL: The cell at row 4 and column 1 is adjacent to the cell at row 5 and column 1.
adjacent(4, 1, 5, 1).
% Rule: r_126cbfeca705  |  line_index: 2  |  NL: The cell at row 4 and column 2 is adjacent to the cell at row 4 and column 3.
adjacent(4, 2, 4, 3).
% Rule: r_30c7e75adeb5  |  line_index: 3  |  NL: The cell at row 4 and column 2 is adjacent to the cell at row 5 and column 1.
adjacent(4, 2, 5, 1).
% Rule: r_c268ddf4f00f  |  line_index: 4  |  NL: The cell at row 4 language and column 2 is adjacent to the cell at row 5 and column 2.
adjacent(4, 2, 5, 2).
% Rule: r_bcc800df5602  |  line_index: 5  |  NL: The cell at row 4 and column 3 is adjacent to the cell at row 4 and column 4.
adjacent(4, 3, 4, 4).
% Rule: r_d8bef16f6b6f  |  line_index: 6  |  NL: The cell at row 4 and column 3 is adjacent to the cell at row 5 and column 2.
adjacent(4, 3, 5, 2).
% Rule: r_3202b25ad787  |  line_index: 7  |  NL: The cell at row 4 and column 3 is adjacent to the cell at row 5 and column 3.
adjacent(4, 3, 5, 3).
% Rule: r_c12a3d06683e  |  line_index: 8  |  NL: The cell at row 4 and column 4 is adjacent to the cell at row 4 and column 5.
adjacent(4, 4, 4, 5).
% Rule: r_efc060b798f1  |  line_index: 9  |  NL: The cell at row 4 and column 4 is adjacent to the cell at row 5 and column 3.
adjacent(4, 4, 5, 3).