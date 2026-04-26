% Bundle: symtex_batch_20260421_192903Z_23a882e0

% Rule: r_cace532777c2  |  line_index: 0  |  NL: Arrive is explicitly false.
-arrive.

% Rule: r_fd21ede045c2  |  line_index: 1  |  NL: Caste is explicitly false.
-caste.

% Rule: r_9fdbb2625eea  |  line_index: 2  |  NL: Financial institution is explicitly false.
-financial_institution.

% Rule: r_86f441234005  |  line_index: 3  |  NL: Fuzzy is explicitly false.
-fuzzy.

% Rule: r_d9cc1a5e8633  |  line_index: 4  |  NL: Honeycreeper is explicitly false.
-honeycreeper.

% Rule: r_e9828dd1bc29  |  line_index: 5  |  NL: Lifting things is explicitly false.
-lifting_things.

% Rule: r_bec699278f14  |  line_index: 6  |  NL: Lumberjack is explicitly false.
-lumberjack.

% Rule: r_a890a88d95e8  |  line_index: 7  |  NL: Menorrhea is explicitly false.
-menorrhea.

% Rule: r_cbee74f0806e  |  line_index: 8  |  NL: Quagga is explicitly false.
-quagga.

% Rule: r_8dd4af12eb6b  |  line_index: 9  |  NL: Snow is explicitly false.
-snow.

% Rule: r_2caba6189656  |  line_index: 10  |  NL: Spoon is explicitly false.
-spoon.

% Rule: r_171aab24470f  |  line_index: 11  |  NL: Stoner is explicitly false.
-stoner.

% Rule: r_676a6b407406  |  line_index: 12  |  NL: Store farm equipment and animals is explicitly false.
-store_farm_equipment_and_animals.

% Rule: r_8956ce96fbe9  |  line_index: 13  |  NL: Burn bag is true.
burn_bag.

% Rule: r_4afea342f192  |  line_index: 14  |  NL: China is true.
china.

% Rule: r_98973a2a9c86  |  line_index: 15  |  NL: Digging is true.
digging.

% Rule: r_c9ce12331dd3  |  line_index: 16  |  NL: Elderberry is true.
elderberry.

% Rule: r_ea92fa2257fa  |  line_index: 17  |  NL: Entrance is true.
entrance.

% Rule: r_af788951377c  |  line_index: 18  |  NL: Ewe is true.
ewe.

% Rule: r_35f995a4609f  |  line_index: 19  |  NL: Race is true.
race.

% Rule: r_434c8aa55f50  |  line_index: 20  |  NL: Skull and crossbones is true.
skull_and_crossbones.

% Rule: r_7e9398a25b0e  |  line_index: 21  |  NL: Spur is true.
spur.

% Rule: r_843abf27cd8c  |  line_index: 22  |  NL: Wear sweater is true.
wear_sweater.

% Rule: r_f526d8911398  |  line_index: 23  |  NL: If there is no evidence that spoon is true, and there is no evidence that race is explicitly false, and there is no evidence that menorrhea is true, and entrance is true, then center is explicitly false.
-center :- not spoon, not -race, not menorrhea, entrance.

% Rule: r_e54d006be874  |  line_index: 24  |  NL: If dishes is explicitly false, and there is no evidence that writing story is explicitly false, and there is no evidence that salmon is true, and there is no evidence that possible is true, and there is no evidence that commander is true, then digging is explicitly false.
-digging :- -dishes, not -writing_story, not salmon, not possible, not commander.

% Rule: r_68c2abc404d6  |  line_index: 25  |  NL: If spur is true, then eddy is explicitly false.
-eddy :- spur.

% Rule: r_21dbe66d2dd2  |  line_index: 26  |  NL: If spur is true, then georgia is explicitly false.
-georgia :- spur.

% Rule: r_e75aa5560080  |  line_index: 27  |  NL: If commander is true, and there is no evidence that snow is true, and there is no evidence that lifting things is true, and there is no evidence that china is explicitly false, and there is no evidence that fuzzy is true, then pear is explicitly false.
-pear :- commander, not snow, not lifting_things, not -china, not fuzzy.

% Rule: r_ce3938b98da0  |  line_index: 28  |  NL: If dishes is true, and there is no evidence that writing story is true, and there is no evidence that georgia is true, then repeat is explicitly false.
-repeat :- dishes, not writing_story, not georgia.

% Rule: r_aec8f76365ad  |  line_index: 29  |  NL: If basket star is explicitly false, and there is no evidence that eddy is explicitly false, and there is no evidence that lumberjack is true, and there is no evidence that financial institution is true, then skeletal structure is explicitly false.
-skeletal_structure :- -basket_star, not -eddy, not lumberjack, not financial_institution.

% Rule: r_ea77ea7b0b8b  |  line_index: 30  |  NL: If there is no evidence that petitioner is true, and there is no evidence that writing story is explicitly false, and repeat is true, then spur is explicitly false.
-spur :- not petitioner, not -writing_story, repeat.

% Rule: r_1c61b7d117f4  |  line_index: 31  |  NL: If honeycreeper is explicitly false, and there is no evidence that digging is explicitly false, and there is no evidence that wear sweater is explicitly false, and there is no evidence that burn bag is explicitly false, and there is no evidence that arrive is true, then victimless crime is explicitly false.
-victimless_crime :- -honeycreeper, not -digging, not -wear_sweater, not -burn_bag, not arrive.

% Rule: r_9025318028af  |  line_index: 32  |  NL: If petitioner is true, and there is no evidence that victimless crime is true, and there is no evidence that possible is explicitly false, and there is no evidence that beer mug is explicitly false, and there is no evidence that quagga is true, then writing story is explicitly false.
-writing_story :- petitioner, not victimless_crime, not -possible, not -beer_mug, not quagga.

% Rule: r_0c15ca96772f  |  line_index: 33  |  NL: If pear is explicitly false, then basket star is true.
basket_star :- -pear.

% Rule: r_1ccf744cd386  |  line_index: 34  |  NL: If stoner is explicitly false, then beer mug is true.
beer_mug :- -stoner.

% Rule: r_5b111083365d  |  line_index: 35  |  NL: If eddy is explicitly false and there is no evidence that caste is true, then commander is true.
commander :- -eddy, not caste.

% Rule: r_44186527a5cd  |  line_index: 36  |  NL: If honeycreeper is explicitly false, and there is no evidence that digging is explicitly false, and there is no evidence that wear sweater is explicitly false, and there is no evidence that burn bag is explicitly false, and there is no evidence that arrive is true, then dishes is true.
dishes :- -honeycreeper, not -digging, not -wear_sweater, not -burn_bag, not arrive.

% Rule: r_e256a9e3d568  |  line_index: 37  |  NL: If victimless crime is true, and there is no evidence that writing story is explicitly false, and there is no evidence that salmon is true, and there is no evidence that possible is true, and pear is true, then fuzzy is true.
fuzzy :- victimless_crime, not -writing_story, not salmon, not possible, pear.

% Rule: r_38d7052288b2  |  line_index: 38  |  NL: If there is no evidence that store farm equipment and animals is true and elderberry is true, then golf is true.
golf :- not store_farm_equipment_and_animals, elderberry.

% Rule: r_9696c55e6e82  |  line_index: 39  |  NL: If beer mug is explicitly false and repeat is true, then honeycreeper is true.
honeycreeper :- -beer_mug, repeat.

% Rule: r_dd09fa2d021d  |  line_index: 40  |  NL: If victimless crime is true, and writing story is true, and salmon is explicitly false, and skull and crossbones is true, then pear is true.
pear :- victimless_crime, writing_story, -salmon, skull_and_crossbones.

% Rule: r_27555d1f4245  |  line_index: 41  |  NL: If basket star is true, and there is no evidence that salmon is explicitly false, and there is no evidence that eddy is true, and there is no evidence that ewe is explicitly false, then petitioner is true.
petitioner :- basket_star, not -salmon, not eddy, not -ewe.

% Rule: r_b7b77cd3ae89  |  line_index: 42  |  NL: If eddy is explicitly false and there is no evidence that caste is true, then possible is true.
possible :- -eddy, not caste.

% Rule: r_279ba3dfbc8d  |  line_index: 43  |  NL: If there is no evidence that dishes is true, and georgia is true, and beer mug is explicitly false, then repeat is true.
repeat :- not dishes, georgia, -beer_mug.

% Rule: r_fb8568f8904a  |  line_index: 44  |  NL: If there is no evidence that petitioner is true, and basket star is explicitly false, and there is no evidence that salmon is true, then repeat is true.
repeat :- not petitioner, -basket_star, not salmon.

% Rule: r_9a01f9215bbb  |  line_index: 45  |  NL: If eddy is explicitly false and there is no evidence that caste is true, then salmon is true.
salmon :- -eddy, not caste.