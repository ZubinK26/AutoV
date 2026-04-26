- cavy("Sarah", "Nicole").
- sleep("Claire", "Lindsey").
agent("Lindsey", "Nicole").
bird("Lindsey", "Sarah").
crow("Claire", "Lindsey").
dressing_sack("Sarah", "Nicole").
fish("Sarah", "Nicole").
halitus("Claire", "Sarah").
kite("Lindsey", "Sarah").
little_office("Sarah", "Nicole").
sex("Claire").
singing("Claire").
- action(V1) :- fly(V1, V2), - activity(V2, V3).
- breath(V1, V2) | - activity(V2, V3) | feel_good(V0) :- sex(V0), singing(V0), - sleep(V0, V1), halitus(V0, V2), agent(V1, V3).
- flying(V2) | fly(V1, V2) :- bird(V1, V2), not -kite(V1, V2).
- night(V0, V3) :- bat(V1, V2), feel_good(V0), bed(V1, V3), not owl(V0), not sleep(V0, V1).
- owl(V3) :- gobbet(V2, V3), not cavy(V2, V3), not -fish(V2, V3), not -little_office(V2, V3), not -dressing_sack(V2, V3).
- scratching(V1) | bat(V1, V2) | gobbet(V2, V2) :- - flying(V2), - breath(V1, V2), not -kite(V1, V2).
bed(V1, V1) :- - scratching(V1), - breath(V1, V2), not action(V1).
black(V0, V1) :- crow(V0, V1).
dark(V0) :- black(V0, V1), - night(V0, V3).