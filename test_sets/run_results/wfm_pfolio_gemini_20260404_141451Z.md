# WFM automated run — P-FOLIO base text (PF-*), Agents 1 → 2 → 3, Gemini

**UTC timestamp:** 20260404_141451Z

## Contract (this run)

- **Example set:** `pfolio` (P-FOLIO base text, PF-* blocks in source markdown)
- **Model:** `gemini-3.1-pro-preview`
- **Temperature:** `0.0`
- **Max output tokens:** `16384`
- **Thinking level:** `LOW` (see `GEMINI_THINKING_LEVEL`; default is `low` for parity with non–extended-thinking Claude runs)
- **Compound operator limit (injected):** `8`
- **Agent 4:** skipped (no user disagreement simulation)

Full table: `test_sets/wfm_api_contract_gemini.md`

---

## PF-1 (easy)

### Input

Some affection is love. Some love is positive. In conclusion: Some affection is positive.

### Agent 1

At least one instance of affection is an instance of love. At least one instance of love is positive. In conclusion: At least one instance of affection is positive.

### Agent 2

1. "At least one instance of affection is an instance of love."
2. "At least one instance of love is positive."
3. "In conclusion: At least one instance of affection is positive."

### Agent 3

PASS: 1. "At least one instance of affection is an instance of love."
PASS: 2. "At least one instance of love is positive."
PASS: 3. "In conclusion: At least one instance of affection is positive."

---

## PF-2 (easy)

### Input

All humans are mortal. All Greeks are humans. In conclusion: Some Greeks are mortal.

### Agent 1

Every human is mortal. Every Greek is a human. Therefore, at least one Greek is mortal.

### Agent 2

1. "Every human is mortal."
2. "Every Greek is a human."
3. "Therefore, at least one Greek is mortal."

### Agent 3

PASS: 1. "Every human is mortal."
PASS: 2. "Every Greek is a human."
REWRITE: 3. "At least one Greek is mortal." | DIFF: Removed the discourse marker "Therefore, " to form a standard logical statement; no substantive loss.

---

## PF-3 (medium)

### Input

All rabbits are cute. Some turtles exist. An animal is either a rabbit or a squirrel. If something is skittish, then it is not still. All squirrels are skittish. Rock is still. In conclusion: Rock is a turtle.

### Agent 1

Every rabbit is cute. 
There exists at least one turtle. 
Every animal is either a rabbit or a squirrel. 
If an entity is skittish, then that entity is not still. 
Every squirrel is skittish. 
The entity named Rock is still. 
In conclusion: The entity named Rock is a turtle.

### Agent 2

1. "Every rabbit is cute."
2. "There exists at least one turtle."
3. "Every animal is either a rabbit or a squirrel."
4. "If an entity is skittish, then that entity is not still."
5. "Every squirrel is skittish."
6. "The entity named Rock is still."
7. "In conclusion: The entity named Rock is a turtle."

### Agent 3

PASS: 1. "Every rabbit is cute."
PASS: 2. "There exists at least one turtle."
PASS: 3. "Every animal is either a rabbit or a squirrel."
PASS: 4. "If an entity is skittish, then that entity is not still."
PASS: 5. "Every squirrel is skittish."
PASS: 6. "The entity named Rock is still."
REWRITE: 7. "The entity named Rock is a turtle." | DIFF: Removed the discourse marker "In conclusion:" to form a clean logical proposition; no substantive loss.

---

## PF-4 (medium)

### Input

"Stranger Things" is a popular Netflix show. If a Netflix show is popular, Karen will binge-watch it. If and only if Karen binge-watches a Netflix show, she will download it. Karen does not download "Black Mirror". "Black Mirror" is a Netflix show. If Karen binge-watches a Netflix show, she will share it to Lisa. In conclusion: Karen will share "Stranger Things" to Lisa.

### Agent 1

"Stranger Things" is a popular Netflix show. 
If a Netflix show is popular, Karen binge-watches that Netflix show. 
Karen downloads a Netflix show if and only if Karen binge-watches that Netflix show. 
Karen does not download "Black Mirror". 
"Black Mirror" is a Netflix show. 
If Karen binge-watches a Netflix show, Karen shares that Netflix show with Lisa. 
In conclusion: Karen shares "Stranger Things" with Lisa.

### Agent 2

1. "\"Stranger Things\" is a popular Netflix show."
2. "If a Netflix show is popular, Karen binge-watches that Netflix show."
3. "Karen downloads a Netflix show if and only if Karen binge-watches that Netflix show."
4. "Karen does not download \"Black Mirror\"."
5. "\"Black Mirror\" is a Netflix show."
6. "If Karen binge-watches a Netflix show, Karen shares that Netflix show with Lisa."
7. "In conclusion: Karen shares \"Stranger Things\" with Lisa."

### Agent 3

PASS: "Stranger Things" is a popular Netflix show.
PASS: If a Netflix show is popular, Karen binge-watches that Netflix show.
PASS: Karen downloads a Netflix show if and only if Karen binge-watches that Netflix show.
PASS: Karen does not download "Black Mirror".
PASS: "Black Mirror" is a Netflix show.
PASS: If Karen binge-watches a Netflix show, Karen shares that Netflix show with Lisa.
PASS: In conclusion: Karen shares "Stranger Things" with Lisa.

---

## PF-5 (medium)

### Input

All aliens are extraterrestrial. If someone is from Mars, then they are aliens. No extraterrestrial is human. Everyone from Earth is a human. Marvin cannot be from Earth and from Mars. If Marvin is not from Earth, then Marvin is an extraterrestrial. In conclusion: Marvin is an alien.

### Agent 1

Every alien is an extraterrestrial.
If an entity is from Mars, then that entity is an alien.
No extraterrestrial is a human.
Every entity from Earth is a human.
Marvin is not both from Earth and from Mars.
If Marvin is not from Earth, then Marvin is an extraterrestrial.
Therefore, Marvin is an alien.

### Agent 2

1. "Every alien is an extraterrestrial."
2. "If an entity is from Mars, then that entity is an alien."
3. "No extraterrestrial is a human."
4. "Every entity from Earth is a human."
5. "Marvin is not both from Earth and from Mars."
6. "If Marvin is not from Earth, then Marvin is an extraterrestrial."
7. "Therefore, Marvin is an alien."

### Agent 3

PASS: 1. "Every alien is an extraterrestrial."
PASS: 2. "If an entity is from Mars, then that entity is an alien."
PASS: 3. "No extraterrestrial is a human."
PASS: 4. "Every entity from Earth is a human."
PASS: 5. "Marvin is not both from Earth and from Mars."
PASS: 6. "If Marvin is not from Earth, then Marvin is an extraterrestrial."
PASS: 7. "Therefore, Marvin is an alien."

---

## PF-6 (medium)

### Input

Diamond Mine is a professional wrestling stable, formed in WWE. Roderick Strong leads Diamond Mine. Diamond Mine includes the Creed Brothers, and Ivy Nile. Imperium has a feud with Diamond Mine. In conclusion: Roderick strong leads a professional wrestling stable.

### Agent 1

Diamond Mine is a professional wrestling stable formed in WWE. Roderick Strong leads Diamond Mine. Diamond Mine includes the Creed Brothers and Ivy Nile. Imperium has a feud with Diamond Mine. In conclusion: Roderick Strong leads a professional wrestling stable.

### Agent 2

1. "Diamond Mine is a professional wrestling stable formed in WWE."
2. "Roderick Strong leads Diamond Mine."
3. "Diamond Mine includes the Creed Brothers."
4. "Diamond Mine includes Ivy Nile."
5. "Imperium has a feud with Diamond Mine."
6. "In conclusion: Roderick Strong leads a professional wrestling stable."

### Agent 3

PASS: 1. "Diamond Mine is a professional wrestling stable formed in WWE."
PASS: 2. "Roderick Strong leads Diamond Mine."
PASS: 3. "Diamond Mine includes the Creed Brothers."
PASS: 4. "Diamond Mine includes Ivy Nile."
PASS: 5. "Imperium has a feud with Diamond Mine."
PASS: 6. "In conclusion: Roderick Strong leads a professional wrestling stable."

---

## PF-7 (medium)

### Input

All of Zaha Hadid's design styles are timeless. No mass product design is timeless. Either Zaha Hadid's design style or Kelly Wearstler's design style. All of Kelly Wearstler's design styles are evocative. All of Kelly Wearstler's design styles are dreamy. If a design by Max is timeless, then a design by Max is a mass product design and evocative. In conclusion: A design by Max is a mass product design.

### Agent 1

Every one of Zaha Hadid's design styles is timeless. 
No mass product design is timeless. 
The design style is either Zaha Hadid's design style or Kelly Wearstler's design style. 
Every one of Kelly Wearstler's design styles is evocative. 
Every one of Kelly Wearstler's design styles is dreamy. 
If a design by Max is timeless, then the design by Max is a mass product design and is evocative. 
In conclusion: A design by Max is a mass product design.

### Agent 2

1. "Every one of Zaha Hadid's design styles is timeless."
2. "No mass product design is timeless."
3. "The design style is either Zaha Hadid's design style or Kelly Wearstler's design style."
4. "Every one of Kelly Wearstler's design styles is evocative."
5. "Every one of Kelly Wearstler's design styles is dreamy."
6. "If a design by Max is timeless, then the design by Max is a mass product design."
7. "If a design by Max is timeless, then the design by Max is evocative."
8. "In conclusion: A design by Max is a mass product design."

### Agent 3

PASS: 1. "Every one of Zaha Hadid's design styles is timeless."
PASS: 2. "No mass product design is timeless."
PASS: 3. "The design style is either Zaha Hadid's design style or Kelly Wearstler's design style."
PASS: 4. "Every one of Kelly Wearstler's design styles is evocative."
PASS: 5. "Every one of Kelly Wearstler's design styles is dreamy."
PASS: 6. "If a design by Max is timeless, then the design by Max is a mass product design."
PASS: 7. "If a design by Max is timeless, then the design by Max is evocative."
REWRITE: 8. "A design by Max is a mass product design." | DIFF: Removed "In conclusion: " to leave just the logical claim; no substantive loss.

---

## PF-8 (hard)

### Input

In superhero movies, the good guys always win. The Surprising Adventures of Sir Digby Chicken Caesar is a superhero movie. Good guys fight bad guys and vice versa. Sir Digby fights his nemesis. If a superhero movie is named after a character, that character is a good guy. The Surprising Adventures of Sir Digby Chicken Caesar is named after Sir Digby. If somebody wins a fight, the person they are fighting loses. If a superhero movie is named after a character, that character appears in the movie. In conclusion: Sir Digby’s nemesis loses.

### Agent 1

In every superhero movie, every good guy always wins. The Surprising Adventures of Sir Digby Chicken Caesar is a superhero movie. Every good guy fights bad guys, and every bad guy fights good guys. Sir Digby fights Sir Digby's nemesis. If a superhero movie is named after a character, then that character is a good guy. The Surprising Adventures of Sir Digby Chicken Caesar is named after Sir Digby. If a person wins a fight against another person, then the person they are fighting loses. If a superhero movie is named after a character, then that character appears in that superhero movie. In conclusion: Sir Digby’s nemesis loses.

### Agent 2

1. "In every superhero movie, every good guy always wins."
2. "The Surprising Adventures of Sir Digby Chicken Caesar is a superhero movie."
3. "Every good guy fights bad guys."
4. "Every bad guy fights good guys."
5. "Sir Digby fights Sir Digby's nemesis."
6. "If a superhero movie is named after a character, then that character is a good guy."
7. "The Surprising Adventures of Sir Digby Chicken Caesar is named after Sir Digby."
8. "If a person wins a fight against another person, then the person they are fighting loses."
9. "If a superhero movie is named after a character, then that character appears in that superhero movie."
10. "In conclusion: Sir Digby’s nemesis loses."

### Agent 3

REWRITE: For every superhero movie, every good guy wins. | DIFF: Rephrased into explicit quantifiers; removed "always" as redundant.
PASS: 2. "The Surprising Adventures of Sir Digby Chicken Caesar is a superhero movie."
PASS: 3. "Every good guy fights bad guys."
PASS: 4. "Every bad guy fights good guys."
PASS: 5. "Sir Digby fights Sir Digby's nemesis."
PASS: 6. "If a superhero movie is named after a character, then that character is a good guy."
PASS: 7. "The Surprising Adventures of Sir Digby Chicken Caesar is named after Sir Digby."
PASS: 8. "If a person wins a fight against another person, then the person they are fighting loses."
PASS: 9. "If a superhero movie is named after a character, then that character appears in that superhero movie."
REWRITE: Sir Digby’s nemesis loses. | DIFF: Removed discourse marker "In conclusion:" to leave just the logical claim.

---

## PF-9 (hard)

### Input

Pets are allowed in some managed buildings. A deposit is required to rent an apartment in a managed building. The security deposit can be either equal to one month's rent or more. Fluffy is Tom's cat. Cats are pets. The Olive Garden is a managed building. The monthly rent at the Olive Garden is $2000. Tom will rent an apartment in a managed building if and only if he is allowed to move in with Fluffy, and the security deposit is no more than $1500. 2000$ is more than $1500. In conclusion: Tom will rent an apartment in The Olive Garden.

### Agent 1

Pets are allowed in at least one managed building. 
A security deposit is required to rent an apartment in any managed building. 
The security deposit for an apartment is greater than or equal to one month's rent for that apartment. 
Fluffy is a cat, and Tom owns Fluffy. 
Every cat is a pet. 
The Olive Garden is a managed building. 
The monthly rent for an apartment at The Olive Garden is $2000. 
Tom will rent an apartment in a managed building if and only if Tom is allowed to move into that apartment with Fluffy, and the security deposit for that apartment is less than or equal to $1500. 
$2000 is greater than $1500. 
In conclusion: Tom will rent an apartment in The Olive Garden.

### Agent 2

1. "Pets are allowed in at least one managed building."
2. "A security deposit is required to rent an apartment in any managed building."
3. "The security deposit for an apartment is greater than or equal to one month's rent for that apartment."
4. "Fluffy is a cat."
5. "Tom owns Fluffy."
6. "Every cat is a pet."
7. "The Olive Garden is a managed building."
8. "The monthly rent for an apartment at The Olive Garden is $2000."
9. "Tom will rent an apartment in a managed building if and only if Tom is allowed to move into that apartment with Fluffy, and the security deposit for that apartment is less than or equal to $1500."
10. "$2000 is greater than $1500."
11. "In conclusion: Tom will rent an apartment in The Olive Garden."

### Agent 3

PASS: 1. "Pets are allowed in at least one managed building."
PASS: 2. "A security deposit is required to rent an apartment in any managed building."
PASS: 3. "The security deposit for an apartment is greater than or equal to one month's rent for that apartment."
PASS: 4. "Fluffy is a cat."
PASS: 5. "Tom owns Fluffy."
PASS: 6. "Every cat is a pet."
PASS: 7. "The Olive Garden is a managed building."
PASS: 8. "The monthly rent for an apartment at The Olive Garden is $2000."
PASS: 9. "Tom will rent an apartment in a managed building if and only if Tom is allowed to move into that apartment with Fluffy, and the security deposit for that apartment is less than or equal to $1500."
PASS: 10. "$2000 is greater than $1500."
PASS: 11. "In conclusion: Tom will rent an apartment in The Olive Garden."

---

## PF-10 (hard)

### Input

If a man is taller than another man, the taller one can block the other's shooting. Michael is a man who is taller than everyone else in his class. If person x is taller than person y, and person y is taller than person z, then x is taller than z. Peter is a man who is taller than Michael. Michael can block any shooting from a person as long as the person does not jump when shooting. Michael cannot block Windy's shooting. Every shooter who can jump when shooting is a great shooter. In conclusion: Peter is shorter than a man in Michael's class.

### Agent 1

If a man is taller than another man, then the taller man can block the shorter man's shooting. 
Michael is a man who is taller than every other person in Michael's class. 
For every person x, person y, and person z, if person x is taller than person y and person y is taller than person z, then person x is taller than person z. 
Peter is a man who is taller than Michael. 
For every person, if the person does not jump when shooting, then Michael can block that person's shooting. 
Michael cannot block Windy's shooting. 
Every person who shoots and can jump when shooting is a great shooter. 
In conclusion: Peter is shorter than at least one man in Michael's class.

### Agent 2

1. "If a man is taller than another man, then the taller man can block the shorter man's shooting."
2. "Michael is a man who is taller than every other person in Michael's class."
3. "For every person x, person y, and person z, if person x is taller than person y and person y is taller than person z, then person x is taller than person z."
4. "Peter is a man who is taller than Michael."
5. "For every person, if the person does not jump when shooting, then Michael can block that person's shooting."
6. "Michael cannot block Windy's shooting."
7. "Every person who shoots and can jump when shooting is a great shooter."
8. "In conclusion: Peter is shorter than at least one man in Michael's class."

### Agent 3

PASS: 1. "If a man is taller than another man, then the taller man can block the shorter man's shooting."
PASS: 2. "Michael is a man who is taller than every other person in Michael's class."
PASS: 3. "For every person x, person y, and person z, if person x is taller than person y and person y is taller than person z, then person x is taller than person z."
PASS: 4. "Peter is a man who is taller than Michael."
PASS: 5. "For every person, if the person does not jump when shooting, then Michael can block that person's shooting."
PASS: 6. "Michael cannot block Windy's shooting."
PASS: 7. "Every person who shoots and can jump when shooting is a great shooter."
PASS: 8. "In conclusion: Peter is shorter than at least one man in Michael's class."

---
