% Bundle: hard_F_10_20260420_155111Z_b33172f7
person(beethoven).
music_piece(symphony_no_9).
orchestra(vienna_music_society).
conductor(beethoven).

% Rule: r_7570eb6b3a92  |  line_index: 0  |  NL: Symphony No. 9 is a music piece.
music_piece(symphony_no_9).

% Rule: r_f9c2048967af  |  line_index: 1  |  NL: For every person: if the person writes a music piece, then the person is a composer.
composer(P) :- person(P), music_piece(M), writes(P, M).

% Rule: r_cacf5de23370  |  line_index: 2  |  NL: Beethoven wrote Symphony No. 9.
writes(beethoven, symphony_no_9).

% Rule: r_0eb0a833e6d5  |  line_index: 3  |  NL: The Vienna Music Society premiered Symphony No. 9.
premiered(vienna_music_society, symphony_no_9).

% Rule: r_50e11f2d62cd  |  line_index: 4  |  NL: The Vienna Music Society is an orchestra.
orchestra(vienna_music_society).

% Rule: r_3bf1a5b4cd73  |  line_index: 5  |  NL: Beethoven leads the Vienna Music Society.
leads(beethoven, vienna_music_society).

% Rule: r_e080d04798ad  |  line_index: 6  |  NL: For every orchestra, there exists exactly one conductor who leads that orchestra.
1 { leads(C, O) : conductor(C) } 1 :- orchestra(O).

% Rule: r_25a999456f69  |  line_index: 7  |  NL: Beethoven is a composer.
composer(beethoven).