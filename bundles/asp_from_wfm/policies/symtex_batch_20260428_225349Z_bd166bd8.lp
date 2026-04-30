% Bundle: symtex_batch_20260428_225349Z_bd166bd8
% Rule: r_c8409f07a7a6  |  line_index: 0  |  NL: bit is explicitly false.
-bit.
% Rule: r_e7ab6c6c625e  |  line_index: 1  |  NL: bones is explicitly false.
-bones.
% Rule: r_c703b1d4b4d3  |  line_index: 2  |  NL: butter is explicitly false.
-butter.
% Rule: r_ae31ec27149d  |  line_index: 3  |  NL: chicken is explicitly false.
-chicken.
% Rule: r_84354e8b731a  |  line_index: 4  |  NL: earning_money is explicitly false.
-earning_money.
% Rule: r_d9ef7a941a57  |  line_index: 5  |  NL: en is explicitly false.
-en.
% Rule: r_d726eda715fe  |  line_index: 6  |  NL: fairy_godmother is explicitly false.
-fairy_godmother.
% Rule: r_ee6370cdc8cb  |  line_index: 7  |  NL: homogenized_milk is explicitly false.
-homogenized_milk.
% Rule: r_4c3c82051cda  |  line_index: 8  |  NL: point is explicitly false.
-point.
% Rule: r_20332ae337a2  |  line_index: 9  |  NL: position is explicitly false.
-position.
% Rule: r_165dee0df1b9  |  line_index: 10  |  NL: training is explicitly false.
-training.
% Rule: r_32aaf1c7350f  |  line_index: 11  |  NL: breakfast_lunch_and_dinner is true.
breakfast_lunch_and_dinner.
% Rule: r_1e4620a64508  |  line_index: 12  |  NL: freezing is true.
freezing.
% Rule: r_531caa31771d  |  line_index: 13  |  NL: prodigy is true.
prodigy.
% Rule: r_5f3d1e731356  |  line_index: 14  |  NL: rockets is true.
rockets.
% Rule: r_a5c4fb539b34  |  line_index: 15  |  NL: If barn is true and there is no evidence that em is true and there is no evidence that byte is true, then area_unit is explicitly false.
-area_unit :- barn, not em, not byte.
% Rule: r_acb580e843f7  |  line_index: 16  |  NL: If nybble is explicitly false and there is no evidence that bit is true and there is no evidence that bones is true, then byte is explicitly false.
-byte :- -nybble, not bit, not bones.
% Rule: r_941e3deb8378  |  line_index: 17  |  NL: If crest is explicitly false and there is no evidence that byte is true and there is no evidence that prodigy is explicitly false, then computer_memory_unit is explicitly false.
-computer_memory_unit :- -crest, not byte, not -prodigy.
% Rule: r_d9d53a1a2bc0  |  line_index: 18  |  NL: If en is explicitly false and there is no evidence that earning_money is true and there is no evidence that training is true, then crest is explicitly false.
-crest :- -en, not earning_money, not training.
% Rule: r_3067dc5f4ce0  |  line_index: 19  |  NL: If en is explicitly false and there is no evidence that earning_money is true and there is no evidence that training is true, then em is explicitly false.
-em :- -en, not earning_money, not training.
% Rule: r_1cd3b4036eb3  |  line_index: 20  |  NL: If chicken is explicitly false and there is no evidence that freezing is explicitly false and there is no evidence that breakfast_lunch_and_dinner is explicitly false, then meals is explicitly false.
-meals :- -chicken, not -freezing, not -breakfast_lunch_and_dinner.
% Rule: r_e5ab31c204cd  |  line_index: 21  |  NL: If position is explicitly false and there is no evidence that fairy_godmother is true and there is no evidence that rockets is explicitly false, then nybble is explicitly false.
-nybble :- -position, not fairy_godmother, not -rockets.
% Rule: r_97eafba91caa  |  line_index: 22  |  NL: If meals is explicitly false and there is no evidence that satisfying_needs is explicitly false and there is no evidence that computer_memory_unit is true, then scalded_milk is explicitly false.
-scalded_milk :- -meals, not -satisfying_needs, not computer_memory_unit.
% Rule: r_e6b08e5ea6a4  |  line_index: 23  |  NL: If chicken is explicitly false and there is no evidence that freezing is explicitly false and there is no evidence that breakfast_lunch_and_dinner is explicitly false, then barn is true.
barn :- -chicken, not -freezing, not -breakfast_lunch_and_dinner.
% Rule: r_ff2ad5aeb185  |  line_index: 24  |  NL: If milk is true and there is no evidence that prodigy is explicitly false and there is no evidence that butter is true, then dairy_product is true.
dairy_product :- milk, not -prodigy, not butter.
% Rule: r_996220639d4b  |  line_index: 25  |  NL: If unit_of_measurement is true and there is no evidence that scalded_milk is true and there is no evidence that homogenized_milk is true, then milk is true.
milk :- unit_of_measurement, not scalded_milk, not homogenized_milk.
% Rule: r_7df62e43de96  |  line_index: 26  |  NL: If en is explicitly false and there is no evidence that earning_money is true and there is no evidence that training is true, then satisfying_needs is true.
satisfying_needs :- -en, not earning_money, not training.
% Rule: r_a7c216028928  |  line_index: 27  |  NL: If area_unit is explicitly false and there is no evidence that bit is true and there is no evidence that point is true, then unit_of_measurement is true.
unit_of_measurement :- -area_unit, not bit, not point.