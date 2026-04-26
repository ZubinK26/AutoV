- born("Shelley").
- crossing("Rose").
- die_horribly("Rose", "Tara").
- fur("Cynthia", "Shelley").
- modification.
- night_time("Rose", "Shelley").
- offerer("Shelley").
- thysanuran_insect("Cynthia").
double_bed("Rose", "Shelley").
mailbox("Cynthia", "Rose").
moo("Cynthia", "Rose").
traveling_faster("Cynthia", "Tara").
trunk("Shelley", "Tara").
tugboat("Rose", "Shelley").
work_place("Rose", "Shelley").
- body_armor(V2) :- - crossing(V1), mailbox(V0, V1), traveling_faster(V0, V3), - night_time(V1, V2), not -trunk(V2, V3).
- cliffhanger(V1, V3) :- stepladder(V3), guinea_worm(V0, V1), not modification.
- course(V1) :- - cliffhanger(V1, V2), body_armor(V2), guinea_worm(V0, V1), - playing_with_friends(V2).
- course(V1) :- stepladder(V3), guinea_worm(V0, V1), - playing_with_friends(V2).
- guinea_worm(V2, V1) :- cliffhanger(V1, V2).
- mailbox(V2, V1) :- sandwich_shop(V1, V2), stepladder(V3), - palm(V1, V2), - nit(V1, V2), not breadbasket(V1, V3).
- name_puppy(V1, V2) :- - thysanuran_insect(V0), moo(V0, V1), work_place(V1, V2), double_bed(V1, V2), - die_horribly(V1, V3).
- palm(V1, V1) :- - course(V1).
- sandwich_shop(V1, V2) :- - crossing(V1), mailbox(V0, V1), traveling_faster(V0, V3), - night_time(V1, V2), not -trunk(V2, V3).
- shetland_pony(V0, V1) :- - fur(V0, V2), tugboat(V1, V2).
- stepladder(V1) :- - sandwich_shop(V1, V2), not -palm(V1, V2), not -nit(V1, V2).
- traveling_faster(V2, V2) :- body_armor(V2), - born(V2), - offerer(V2).
body_armor(V2) :- not cliffhanger(V1, V2), stepladder(V3), - nit(V1, V2).
breadbasket(V2, V2) :- - body_armor(V2), not -playing_with_friends(V2).
cliffhanger(V1, V2) :- - crossing(V1), mailbox(V0, V1), traveling_faster(V0, V3), - night_time(V1, V2), not -trunk(V2, V3).
course(V1) :- - stepladder(V3), - guinea_worm(V0, V1), not -breadbasket(V1, V3).
night_time(V1, V2) :- sandwich_shop(V1, V2), - cliffhanger(V1, V2), body_armor(V2), - breadbasket(V1, V3), not course(V1).
nit(V1, V2) :- palm(V1, V2).
palm(V1, V2) :- cliffhanger(V1, V2).
playing_with_friends(V2) :- cliffhanger(V1, V2).