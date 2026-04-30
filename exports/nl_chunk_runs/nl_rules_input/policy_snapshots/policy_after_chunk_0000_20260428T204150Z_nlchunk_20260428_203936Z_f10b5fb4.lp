% Bundle: nlchunk_20260428_203936Z_f10b5fb4

% Rule: r_21a6349b55f5  |  line_index: 0  |  NL: Every creature either has a specific condition or does not have that condition.
{ holds(condition(C, Cond), T) } :- creature(C), condition_type(Cond), time(T).

% Rule: r_ab5b03a32ab3  |  line_index: 1  |  NL: When multiple effects impose the same condition on a creature, each instance of that condition has its own duration.
holds(instance_duration(C, Cond, EffectID, Dur), T) :- occurs(impose_condition(EffectID, C, Cond, Dur), T).

% Rule: r_201fd7e5d4e2  |  line_index: 2  |  NL: When multiple effects impose the same condition on a creature, the effects of that condition do not stack beyond the effects of a single instance.
holds(condition(C, Cond), T) :- holds(instance_duration(C, Cond, EffectID, Dur), T), Dur > 0.

% Rule: r_dd2c99b2457a  |  line_index: 3  |  NL: A condition ends when a specified action counters it.
-holds(instance_duration(C, Cond, EffectID, Dur), T+1) :- holds(instance_duration(C, Cond, EffectID, Dur), T), occurs(counter_action(A, C, Cond), T).

% Rule: r_56fa85a61198  |  line_index: 4  |  NL: A condition ends when its duration expires.
-holds(instance_duration(C, Cond, EffectID, 0), T+1) :- holds(instance_duration(C, Cond, EffectID, 0), T).

% Rule: r_610e49bf4de5  |  line_index: 5  |  NL: Every blinded creature cannot see.
-can_see(C, T) :- holds(condition(C, blinded), T).

% Rule: r_7e8da997e385  |  line_index: 6  |  NL: Every blinded creature fails every ability check that requires sight.
fails_check(C, Check, T) :- holds(condition(C, blinded), T), requires_sight(Check).

% Rule: r_0c0b7781e460  |  line_index: 7  |  NL: Every attack roll made against a blinded creature has advantage.
has_advantage(attack_roll(Attacker, C), T) :- holds(condition(C, blinded), T), creature(Attacker).

% Rule: r_07d2ef47c57a  |  line_index: 8  |  NL: Every attack roll made by a blinded creature has disadvantage.
has_disadvantage(attack_roll(C, Target), T) :- holds(condition(C, blinded), T), creature(Target).

% Rule: r_2dfde8c5d79d  |  line_index: 9  |  NL: Every charmed creature cannot make an attack roll that targets the charmer.
-can_perform(attack_roll(C, Charmer), T) :- holds(condition(C, charmed(Charmer)), T).

% Rule: r_b0970631b936  |  line_index: 10  |  NL: Every charmed creature cannot target the charmer with any harmful ability.
-can_target(C, Charmer, Ability, T) :- holds(condition(C, charmed(Charmer)), T), harmful(Ability).

% Rule: r_dc6eefaaef32  |  line_index: 11  |  NL: Every charmed creature cannot target the charmer with any harmful magical effect.
-can_target(C, Charmer, Effect, T) :- holds(condition(C, charmed(Charmer)), T), harmful(Effect), magical(Effect).

% Rule: r_0d4ed150f1e9  |  line_index: 12  |  NL: Every ability check that the charmer makes to interact socially with the charmed creature has advantage.
has_advantage(ability_check(Charmer, social_interaction, C), T) :- holds(condition(C, charmed(Charmer)), T).

% Rule: r_342cd11c87cc  |  line_index: 13  |  NL: Every deafened creature cannot hear.
-can_hear(C, T) :- holds(condition(C, deafened), T).

% Rule: r_6d794daa42cc  |  line_index: 14  |  NL: Every deafened creature fails every ability check that requires hearing.
fails_check(C, Check, T) :- holds(condition(C, deafened), T), requires_hearing(Check).

% Rule: r_653b3b72aeca  |  line_index: 15  |  NL: Every creature has an exhaustion level that is an integer between 0 and 6 inclusive.
1 { holds(exhaustion_level(C, L), T) : L=0..6 } 1 :- creature(C), time(T).

% Rule: r_ba887d57454f  |  line_index: 16  |  NL: A creature with an exhaustion level of 0 is not exhausted.
-holds(condition(C, exhausted), T) :- holds(exhaustion_level(C, 0), T).

% Rule: r_41f1b2d67cc5  |  line_index: 17  |  NL: When an effect imposes exhaustion on a creature, the creature's exhaustion level increases by the amount specified by that effect.
holds(exhaustion_level(C, L2), T+1) :- holds(exhaustion_level(C, L1), T), occurs(impose_exhaustion(C, V), T), L2 = L1 + V, L2 <= 6.

% Rule: r_9eff9eb889c7  |  line_index: 18  |  NL: A creature's exhaustion level cannot exceed 6.
:- holds(exhaustion_level(C, L), T), L > 6.

% Rule: r_b15a4ea8bad7  |  line_index: 19  |  NL: A creature with an exhaustion level of 6 dies.
occurs(die(C), T) :- holds(exhaustion_level(C, 6), T).

% Rule: r_618f3ee63fa5  |  line_index: 20  |  NL: A creature with an exhaustion level of 5 or higher has a speed of 0.
holds(speed(C, 0), T) :- holds(exhaustion_level(C, L), T), L >= 5.

% Rule: r_9644201c45f7  |  line_index: 21  |  NL: A creature with an exhaustion level of 4 or higher has a hit point maximum equal to half of its normal hit point maximum, rounded down.
holds(hp_max(C, V/2), T) :- holds(exhaustion_level(C, L), T), L >= 4, holds(normal_hp_max(C, V), T).

% Rule: r_222b01d7b0be  |  line_index: 22  |  NL: A creature with an exhaustion level of 3 or higher has disadvantage on every attack roll.
has_disadvantage(attack_roll(C, Target), T) :- holds(exhaustion_level(C, L), T), L >= 3, creature(Target).

% Rule: r_4ff8a1b70ace  |  line_index: 23  |  NL: A creature with an exhaustion level of 3 or higher has disadvantage on every saving throw.
has_disadvantage(saving_throw(C, Stat), T) :- holds(exhaustion_level(C, L), T), L >= 3, stat(Stat).

% Rule: r_0ad48d7001ba  |  line_index: 24  |  NL: A creature with an exhaustion level of 2 or higher has a speed equal to half of its normal speed, rounded down.
holds(speed(C, V/2), T) :- holds(exhaustion_level(C, L), T), L >= 2, L < 5, holds(normal_speed(C, V), T).

% Rule: r_5d8cbe76c0d7  |  line_index: 25  |  NL: A creature with an exhaustion level of 1 or higher has disadvantage on every ability check.
has_disadvantage(ability_check(C, Check), T) :- holds(exhaustion_level(C, L), T), L >= 1, ability_check_type(Check).

% Rule: r_0eb01376af9d  |  line_index: 26  |  NL: When an effect removes exhaustion from a creature, the creature's exhaustion level decreases by the amount specified by that effect.
holds(exhaustion_level(C, L2), T+1) :- holds(exhaustion_level(C, L1), T), occurs(remove_exhaustion(C, V), T), L2 = L1 - V, L2 >= 0.

% Rule: r_e402e2013f48  |  line_index: 27  |  NL: If an effect removes exhaustion and the level would fall below 1, it is set to 0.
holds(exhaustion_level(C, 0), T+1) :- holds(exhaustion_level(C, L1), T), occurs(remove_exhaustion(C, V), T), L1 - V < 0.

% Rule: r_f89e72f56e3c  |  line_index: 28  |  NL: If a creature finishes a long rest and has consumed both food and drink during that rest, its exhaustion level decreases by 1.
holds(exhaustion_level(C, L-1), T+1) :- holds(exhaustion_level(C, L), T), occurs(finish_long_rest(C), T), holds(consumed_food(C), T), holds(consumed_drink(C), T), L > 0.

% Rule: r_1dc99b8a8231  |  line_index: 29  |  NL: Every frightened creature has disadvantage on every ability check while the source of its fear is within its line of sight.
has_disadvantage(ability_check(C, Check), T) :- holds(condition(C, frightened(Source)), T), holds(in_line_of_sight(C, Source), T), ability_check_type(Check).

% Rule: r_2f98e15c4a92  |  line_index: 30  |  NL: Every frightened creature has disadvantage on every attack roll while the source of its fear is within its line of sight.
has_disadvantage(attack_roll(C, Target), T) :- holds(condition(C, frightened(Source)), T), holds(in_line_of_sight(C, Source), T), creature(Target).

% Rule: r_82a5d1033a1a  |  line_index: 31  |  NL: Every frightened creature cannot willingly move to any position that is closer to the source of its fear than its current position.
-can_move_to(C, Pos, T) :- holds(condition(C, frightened(Source)), T), holds(position(C, CurrPos), T), holds(position(Source, SourcePos), T), distance(Pos, SourcePos, D1), distance(CurrPos, SourcePos, D2), D1 < D2, willing_move(C, T).

% Rule: r_11f61d961c21  |  line_index: 32  |  NL: Every grappled creature has a speed of 0.
holds(speed(C, 0), T) :- holds(condition(C, grappled(Grappler)), T).

% Rule: r_2b2ae668f9f1  |  line_index: 33  |  NL: Every grappled creature cannot gain any bonus to its speed.
-can_gain_bonus(C, speed, T) :- holds(condition(C, grappled(Grappler)), T).

% Rule: r_1c0cc7793db1  |  line_index: 34  |  NL: A grapple condition on a creature ends if the grappler becomes unable to take actions or reactions.
-holds(condition(C, grappled(Grappler)), T+1) :- holds(condition(C, grappled(Grappler)), T), holds(condition(Grappler, incapacitated), T).

% Rule: r_9ca32fa61030  |  line_index: 35  |  NL: A grapple condition on a creature ends if an effect moves the grappled creature to a position outside the reach of the grappler.
-holds(condition(C, grappled(Grappler)), T+1) :- holds(condition(C, grappled(Grappler)), T), occurs(move(C, Pos), T), holds(position(Grappler, GPos), T), not holds(within_reach(Pos, GPos, Grappler), T).

% Rule: r_a4a3bfe977ac  |  line_index: 36  |  NL: Every creature that cannot take actions and cannot take reactions is incapacitated.
holds(condition(C, incapacitated), T) :- -can_take_action(C, T), -can_take_reaction(C, T), creature(C), time(T).

% Rule: r_c03d93f4d3d8  |  line_index: 37  |  NL: Every invisible creature cannot be seen by any means except through magic or a special sense.
-can_be_seen(C, Observer, T) :- holds(condition(C, invisible), T), creature(Observer), not holds(has_special_sense(Observer), T), not holds(using_magic_vision(Observer), T).

% Rule: r_b356d0945bf9  |  line_index: 38  |  NL: Every invisible creature is treated as heavily obscured for the purpose of determining whether the creature can hide.
can_hide(C, T) :- holds(condition(C, invisible), T).

% Rule: r_a94227385c02  |  line_index: 39  |  NL: The location of an invisible creature can be detected through sounds the creature produces.
can_detect_location(Observer, C, T) :- holds(condition(C, invisible), T), occurs(produce_sound(C), T), creature(Observer).

% Rule: r_ecb8058b50e7  |  line_index: 40  |  NL: The location of an invisible creature can be detected through tracks the creature leaves.
can_detect_location(Observer, C, T) :- holds(condition(C, invisible), T), holds(leaves_tracks(C), T), creature(Observer).

% Rule: r_75e26c21f042  |  line_index: 41  |  NL: Every attack roll made against an invisible creature has disadvantage.
has_disadvantage(attack_roll(Attacker, C), T) :- holds(condition(C, invisible), T), creature(Attacker).

% Rule: r_d359a711860e  |  line_index: 42  |  NL: Every attack roll made by an invisible creature has advantage.
has_advantage(attack_roll(C, Target), T) :- holds(condition(C, invisible), T), creature(Target).

% Rule: r_00b844aaaf01  |  line_index: 43  |  NL: Every paralyzed creature cannot take actions or reactions.
-can_take_action(C, T) :- holds(condition(C, paralyzed), T).
-can_take_reaction(C, T) :- holds(condition(C, paralyzed), T).

% Rule: r_6ae18b2a8999  |  line_index: 44  |  NL: Every paralyzed creature cannot move.
-can_move(C, T) :- holds(condition(C, paralyzed), T).

% Rule: r_6c3769b10189  |  line_index: 45  |  NL: Every paralyzed creature cannot speak.
-can_speak(C, T) :- holds(condition(C, paralyzed), T).

% Rule: r_80ae0f529233  |  line_index: 46  |  NL: Every paralyzed creature fails every Strength saving throw.
fails_saving_throw(C, strength, T) :- holds(condition(C, paralyzed), T).

% Rule: r_fb5e5bbb87f4  |  line_index: 47  |  NL: Every paralyzed creature fails every Dexterity saving throw.
fails_saving_throw(C, dexterity, T) :- holds(condition(C, paralyzed), T).

% Rule: r_c1c0341540ec  |  line_index: 48  |  NL: Every attack roll made against a paralyzed creature has advantage.
has_advantage(attack_roll(Attacker, C), T) :- holds(condition(C, paralyzed), T), creature(Attacker).

% Rule: r_4b5fa115d359  |  line_index: 49  |  NL: Every attack roll that hits a paralyzed creature is a critical hit if the attacker is 5 feet or less from the paralyzed creature.
is_critical_hit(attack_roll(Attacker, C), T) :- holds(condition(C, paralyzed), T), occurs(hit(Attacker, C), T), holds(position(Attacker, P1), T), holds(position(C, P2), T), distance(P1, P2, D), D <= 5.