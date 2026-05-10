There is a board with twenty-five cells.
The cells are identified by row and column, where rows are numbered 1 through 5 and columns are numbered 1 through 5.
Each cell is identified by a pair (R, C) where R is the row and C is the column.
There are four edges of the board: the top edge, the bottom edge, the left edge, and the right edge.
The cells in row 1 are on the top edge.
The cells in row 5 are on the bottom edge.
The cells in column 1 are on the left edge.
The cells in column 5 are on the right edge.
There are two players: red and blue.
The red player is assigned the top edge and the bottom edge.
The blue player is assigned the left edge and the right edge.
The cell at row 1 and column 1 is adjacent to the cell at row 1 and column 2.
The cell at row 1 and column 1 is adjacent to the cell at row 2 and column 1.
The cell at row 1 and column 2 is adjacent to the cell at row 1 and column 3.
The cell at row 1 and column 2 is adjacent to the cell at row 2 and column 1.
The cell at row 1 and column 2 is adjacent to the cell at row 2 and column 2.
The cell at row 1 and column 3 is adjacent to the cell at row 1 and column 4.
The cell at row 1 and column 3 is adjacent to the cell at row 2 and column 2.
The cell at row 1 and column 3 is adjacent to the cell at row 2 and column 3.
The cell at row 1 and column 4 is adjacent to the cell at row 1 and column 5.
The cell at row 1 and column 4 is adjacent to the cell at row 2 and column 3.
The cell at row 1 and column 4 is adjacent to the cell at row 2 and column 4.
The cell at row 1 and column 5 is adjacent to the cell at row 2 and column 4.
The cell at row 1 and column 5 is adjacent to the cell at row 2 and column 5.
The cell at row 2 and column 1 is adjacent to the cell at row 2 and column 2.
The cell at row 2 and column 1 is adjacent to the cell at row 3 and column 1.
The cell at row 2 and column 2 is adjacent to the cell at row 2 and column 3.
The cell at row 2 and column 2 is adjacent to the cell at row 3 and column 1.
The cell at row 2 and column 2 is adjacent to the cell at row 3 and column 2.
The cell at row 2 and column 3 is adjacent to the cell at row 2 and column 4.
The cell at row 2 and column 3 is adjacent to the cell at row 3 and column 2.
The cell at row 2 and column 3 is adjacent to the cell at row 3 and column 3.
The cell at row 2 and column 4 is adjacent to the cell at row 2 and column 5.
The cell at row 2 and column 4 is adjacent to the cell at row 3 and column 3.
The cell at row 2 and column 4 is adjacent to the cell at row 3 and column 4.
The cell at row 2 and column 5 is adjacent to the cell at row 3 and column 4.
The cell at row 2 and column 5 is adjacent to the cell at row 3 and column 5.
The cell at row 3 and column 1 is adjacent to the cell at row 3 and column 2.
The cell at row 3 and column 1 is adjacent to the cell at row 4 and column 1.
The cell at row 3 and column 2 is adjacent to the cell at row 3 and column 3.
The cell at row 3 and column 2 is adjacent to the cell at row 4 and column 1.
The cell at row 3 and column 2 is adjacent to the cell at row 4 and column 2.
The cell at row 3 and column 3 is adjacent to the cell at row 3 and column 4.
The cell at row 3 and column 3 is adjacent to the cell at row 4 and column 2.
The cell at row 3 and column 3 is adjacent to the cell at row 4 and column 3.
The cell at row 3 and column 4 is adjacent to the cell at row 3 and column 5.
The cell at row 3 and column 4 is adjacent to the cell at row 4 and column 3.
The cell at row 3 and column 4 is adjacent to the cell at row 4 and column 4.
The cell at row 3 and column 5 is adjacent to the cell at row 4 and column 4.
The cell at row 3 and column 5 is adjacent to the cell at row 4 and column 5.
The cell at row 4 and column 1 is adjacent to the cell at row 4 and column 2.
The cell at row 4 and column 1 is adjacent to the cell at row 5 and column 1.
The cell at row 4 and column 2 is adjacent to the cell at row 4 and column 3.
The cell at row 4 and column 2 is adjacent to the cell at row 5 and column 1.
The cell at row 4 and column 2 is adjacent to the cell at row 5 and column 2.
The cell at row 4 and column 3 is adjacent to the cell at row 4 and column 4.
The cell at row 4 and column 3 is adjacent to the cell at row 5 and column 2.
The cell at row 4 and column 3 is adjacent to the cell at row 5 and column 3.
The cell at row 4 and column 4 is adjacent to the cell at row 4 and column 5.
The cell at row 4 and column 4 is adjacent to the cell at row 5 and column 3.
The cell at row 4 and column 4 is adjacent to the cell at row 5 and column 4.
The cell at row 4 and column 5 is adjacent to the cell at row 5 and column 4.
The cell at row 4 and column 5 is adjacent to the cell at row 5 and column 5.
The cell at row 5 and column 1 is adjacent to the cell at row 5 and column 2.
The cell at row 5 and column 2 is adjacent to the cell at row 5 and column 3.
The cell at row 5 and column 3 is adjacent to the cell at row 5 and column 4.
The cell at row 5 and column 4 is adjacent to the cell at row 5 and column 5.
If cell X is adjacent to cell Y, then cell Y is adjacent to cell X.
The state of every cell is one of: empty, red, or blue.
At the start of the game, every cell is empty.
Time proceeds in turns numbered 0 through 25.
Turn 0 is the start of the game.
On each turn after turn 0, exactly one player makes a move.
The red player moves on turns 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, and 25.
The blue player moves on turns 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, and 24.
A move by the red player consists of choosing one empty cell and changing its state to red.
A move by the blue player consists of choosing one empty cell and changing its state to blue.
Once a cell has been changed from empty to red, it remains red for the rest of the game.
Once a cell has been changed from empty to blue, it remains blue for the rest of the game.
A red chain is a set of cells such that every cell in the set is in the red state, and for every two cells in the set there is a sequence of cells in the set, starting with the first cell and ending with the second cell, in which each consecutive pair of cells in the sequence are adjacent to each other.
A blue chain is a set of cells such that every cell in the set is in the blue state, and for every two cells in the set there is a sequence of cells in the set, starting with the first cell and ending with the second cell, in which each consecutive pair of cells in the sequence are adjacent to each other.
The red player wins on a turn if there is a red chain that contains at least one cell on the top edge and at least one cell on the bottom edge.
The blue player wins on a turn if there is a blue chain that contains at least one cell on the left edge and at least one cell on the right edge.
The game ends as soon as one player wins.
The game cannot end in a draw.