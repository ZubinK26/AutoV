% Bundle: hard_R_5_20260420_155956Z_b96b26eb

vendor(nimbus_cloud).
criterion(C) :- criterion_adopted_by_board(C).
criterion_adopted_by_board(C) :- criterion_published_in_april_addendum(C).

% Rule: r_d63efc807fc1  |  line_index: 0  |  NL: For every criterion in the set of criteria adopted by the procurement compliance board: if a vendor satisfies that criterion under the board’s published stress-test scenarios and no subsidiary of that vendor is on the sanctions watchlist during the review window, then that vendor qualifies for the restricted federal data path.
qualifies_for_restricted_path(V) :- vendor(V), not has_unsatisfied_criterion(V), not subsidiary_on_sanctions_watchlist(V).
has_unsatisfied_criterion(V) :- vendor(V), criterion_adopted_by_board(C), not satisfies_under_stress_test(V, C).

% Rule: r_c116cd536c0b  |  line_index: 1  |  NL: Nimbus Cloud satisfies every criterion that the board published in the April addendum.
satisfies_under_stress_test(nimbus_cloud, C) :- criterion_published_in_april_addendum(C).

% Rule: r_4519f0941909  |  line_index: 2  |  NL: No subsidiary of Nimbus Cloud appeared on the sanctions watchlist during the review window.
% (Represented by the absence of subsidiary_on_sanctions_watchlist(nimbus_cloud))

% Rule: r_39867a8eac03  |  line_index: 4  |  NL: If Nimbus Cloud is sanction-sensitive, then the offer for the restricted federal data path to Nimbus Cloud is void.
offer_void(nimbus_cloud) :- sanction_sensitive(nimbus_cloud).

% Rule: r_553d33feb21b  |  line_index: 5  |  NL: Nimbus Cloud qualifies for the restricted federal data path.
qualifies_for_restricted_path(nimbus_cloud).

% Rule: r_4931f189cbed  |  line_index: 6  |  NL: The offer for the restricted federal data path to Nimbus Cloud is not void.
:- offer_void(nimbus_cloud).