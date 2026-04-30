acorns("Heather", "James", "Phillip").
brushes("Phillip").
chain_mail("Nicole", "James", "Adam").
check_mark("Heather", "James", "Adam").
coulterneb("Phillip").
hobby("Phillip").
jump_high("Nicole", "James", "Adam").
oven("Nicole", "James", "Adam").
overactivity("Nicole", "Adam", "Phillip").
parcellation("Heather", "James", "Adam").
plums("Phillip").
pooch("Nicole", "James", "Adam").
shrapnel("Nicole", "James", "Phillip").
tufted_puffin("Heather", "James", "Phillip").
uropygium("James", "Phillip").
vireo("Nicole", "James", "Adam").
article(V4) :- shrapnel(V1, V2, V4).
bacon_strip(V0, V2, V3) :- uropygium(V2, V4), parcellation(V0, V2, V3), tufted_puffin(V0, V2, V4).
dame(V1) :- saddle(V1, V2, V3), distillery(V1, V2, V3), vireo(V1, V2, V3).
distillery(V1, V2, V3) :- oven(V1, V2, V3), chain_mail(V1, V2, V3), pooch(V1, V2, V3), jump_high(V1, V2, V3), vireo(V1, V2, V3).
fog(V4) :- dame(V1), retractable_claws(V1, V2), lens_cortex(V3, V4), acorns(V0, V2, V4), overactivity(V1, V3, V4).
having_lunch(V4, V4) :- fog(V4), coulterneb(V4), plums(V4), hobby(V4), brushes(V4).
lemon(V2, V3) :- pine_grosbeak(V3), toes(V3, V4), bacon_strip(V0, V2, V3), ping_pong_ball(V2, V3, V4).
lens_cortex(V3, V3) :- oven(V1, V2, V3), chain_mail(V1, V2, V3), pooch(V1, V2, V3), jump_high(V1, V2, V3), vireo(V1, V2, V3).
pine_grosbeak(V3) :- rock_group(V1, V2, V3).
ping_pong_ball(V2, V3, V4) :- sell_sandwiches(V2, V3), quite(V0, V2, V3), article(V4), having_lunch(V0, V4), hobby(V4).
quite(V0, V2, V3) :- uropygium(V2, V4), parcellation(V0, V2, V3), tufted_puffin(V0, V2, V4).
retractable_claws(V1, V2) :- shrapnel(V1, V2, V4).
rock_group(V2, V2, V3) :- quite(V0, V2, V3), check_mark(V0, V2, V3).
saddle(V1, V2, V3) :- rock_group(V1, V2, V3).
sell_sandwiches(V2, V3) :- dame(V1), retractable_claws(V1, V2), lens_cortex(V3, V4), acorns(V0, V2, V4), overactivity(V1, V3, V4).
toes(V3, V1) :- saddle(V1, V2, V3), distillery(V1, V2, V3), vireo(V1, V2, V3).