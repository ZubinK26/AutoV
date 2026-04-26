- asthenosphere("Shawn").
- black_rat("Judy", "Shawn").
- corn("Mary", "Stephanie").
- corncob("Stephanie", "Shawn").
- field_corn("Mary", "Stephanie").
- rota("Judy", "Ryan", "Shawn").
- wear("Judy", "Stephanie").
deal_drugs("Judy", "Stephanie").
ear("Ryan", "Shawn").
jerboa_rat("Judy", "Shawn").
most_commonly("Judy", "Mary").
radio_operator("Judy", "Ryan", "Mary").
sweet_corn("Ryan", "Mary").
swiss_pine("Judy", "Shawn").
tropopause("Shawn").
- cereal(V1, V2) :- rice(V4), - millet(V4), barley(V0, V1, V2), P7(V2, V3, V4).
- millet(V4) :- bandicoot_rat(V0, V4), not -rice_rat(V0, V4), not -swiss_pine(V0, V4), not -jerboa_rat(V0, V4), not black_rat(V0, V4).
- rat(V0, V4) :- bandicoot_rat(V0, V4), not -rice_rat(V0, V4), not -swiss_pine(V0, V4), not -jerboa_rat(V0, V4), not black_rat(V0, V4).
P7(V2, V3, V4) :- sweet_corn(V1, V2), ear(V1, V4), - corn(V2, V3), not field_corn(V2, V3), not corncob(V3, V4).
bandicoot_rat(V0, V4) :- - rota(V0, V1, V4).
barley(V0, V1, V2) :- most_commonly(V0, V2), - wear(V0, V3), radio_operator(V0, V1, V2).
crust(V4, V4) :- - millet(V4), not asthenosphere(V4).
layer(V4, V4, V4) :- - asthenosphere(V4), not -tropopause(V4).
rice(V4) :- crust(V1, V3), - rat(V2, V3), layer(V1, V3, V4).
rice_rat(V0, V0) :- deal_drugs(V0, V3), not wear(V0, V3).