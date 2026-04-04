# WFM manual test — English examples from FOLIO (and P-FOLIO base text)

Sources: **FOLIO** v0.0 from [Yale-LILY/FOLIO](https://github.com/Yale-LILY/FOLIO) (CC-BY-SA-4.0).

**P-FOLIO note:** The Hugging Face dataset [`yale-nlp/P-FOLIO`](https://huggingface.co/datasets/yale-nlp/P-FOLIO) is **gated** (accept license + login). P-FOLIO builds **human proof chains** on top of the same underlying FOLIO natural-language problems. Until you download `P-FOLIO.csv` into `test_sets/datasets/p-folio/`, the **P-FOLIO section below** uses **additional distinct FOLIO premise bundles** (no duplicate with the first ten), each as one English block—the same NL P-FOLIO annotators used as source material. This is suitable for **Agent 1 / WFM** smoke tests; it does **not** include P-FOLIO step-by-step proofs.

Rough difficulty tags: **easy** / **medium** / **hard** (premise count and structural complexity). `[BG]` background markers from FOLIO are stripped below. A few known FOLIO NL typos are lightly normalized (e.g. tax haven / flu wording) for cleaner manual testing.

---

## FOLIO (10 examples)

### F-1 (easy)

All squares have four sides. All four-sided things are shapes. In conclusion: All squares are shapes.

### F-2 (easy)

All cats are mammals. Some pets are not mammals. In conclusion: No pets are cats.

### F-3 (easy)

All fir trees are evergreens. Some objects of worship are fir trees. In conclusion: Some evergreens are not objects of worship.

### F-4 (medium)

If people perform in school talent shows often, then they attend and are very engaged with school events. People either perform in school talent shows often or are inactive and disinterested members of their community. If people chaperone high school dances, then they are not students who attend the school. All people who are inactive and disinterested members of their community chaperone high school dances. All young children and teenagers who wish to further their academic careers and educational opportunities are students who attend the school. Bonnie either both attends and is very engaged with school events and is a student who attends the school, or she neither attends and is very engaged with school events nor is a student who attends the school. In conclusion: Bonnie performs in school talent shows often.

### F-5 (medium)

Monkeypox is an infectious disease caused by the monkeypox virus. Monkeypox virus can occur in certain animals, including humans. Humans are mammals. Mammals are animals. Symptons of Monkeypox include fever, headache, muscle pains, feeling tired, and so on. People feel tired when they get the flu. In conclusion: There is an animal.

### F-6 (medium)

There are six types of wild turkeys: Eastern wild turkey, Osceola wild turkey, Gould’s wild turkey, Merriam’s wild turkey, Rio Grande wild turkey, and Ocellated wild turkey. Tom is not an Eastern wild turkey. Tom is not an Osceola wild turkey. Tom is also not a Gould's wild turkey, or a Merriam's wild turkey, or a Rio Grande wild turkey. Tom is a wild turkey. In conclusion: Tom is an Ocellated wild turkey.

### F-7 (medium)

A Japanese game company created the game the Legend of Zelda. All games in the Top 10 list are made by Japanese game companies. If a game sells more than one million copies, then it will be selected into the Top 10 list. The Legend of Zelda sold more than one million copies. In conclusion: The Legend of Zelda is in the Top 10 list.

### F-8 (hard)

All employees who schedule a meeting with their customers will appear in the company today. Everyone who has lunch in the company schedules meetings with their customers. Employees will either have lunch in the company or have lunch at home. If an employee has lunch at home, then he/she is working remotely from home. All employees who are in other countries work remotely from home. No managers work remotely from home. James is either a manager and appears in the company today or neither a manager nor appears in the company today. In conclusion: James has lunch in the company.

### F-9 (hard)

A person is either a Grand Slam champion or an Oscar-nominated actor. All people who are Grand Slam champions are professional tennis players. All Oscar-nominated actors are celebrities. All professional tennis players are athletes. If a person is a celebrity then they are well paid. If a person is an athlete then they are famous. All well-paid people live in tax havens. If Djokovic is famous and is an athlete, then Djokovic lives in a tax haven. In conclusion: Djokovic is a Grand Slam champion.

### F-10 (hard)

Symphony No. 9 is a music piece. Composers write music pieces. Beethoven wrote Symphony No. 9. Vienna Music Society premiered Symphony No. 9. Vienna Music Society is an orchestra. Beethoven leads the Vienna Music Society. Orchestras are led by conductors. In conclusion: Beethoven is a composer.

---

## P-FOLIO base text (10 examples; replace with official CSV rows when available)

### PF-1 (easy)

Some affection is love. Some love is positive. In conclusion: Some affection is positive.

### PF-2 (easy)

All humans are mortal. All Greeks are humans. In conclusion: Some Greeks are mortal.

### PF-3 (medium)

All rabbits are cute. Some turtles exist. An animal is either a rabbit or a squirrel. If something is skittish, then it is not still. All squirrels are skittish. Rock is still. In conclusion: Rock is a turtle.

### PF-4 (medium)

"Stranger Things" is a popular Netflix show. If a Netflix show is popular, Karen will binge-watch it. If and only if Karen binge-watches a Netflix show, she will download it. Karen does not download "Black Mirror". "Black Mirror" is a Netflix show. If Karen binge-watches a Netflix show, she will share it to Lisa. In conclusion: Karen will share "Stranger Things" to Lisa.

### PF-5 (medium)

All aliens are extraterrestrial. If someone is from Mars, then they are aliens. No extraterrestrial is human. Everyone from Earth is a human. Marvin cannot be from Earth and from Mars. If Marvin is not from Earth, then Marvin is an extraterrestrial. In conclusion: Marvin is an alien.

### PF-6 (medium)

Diamond Mine is a professional wrestling stable, formed in WWE. Roderick Strong leads Diamond Mine. Diamond Mine includes the Creed Brothers, and Ivy Nile. Imperium has a feud with Diamond Mine. In conclusion: Roderick strong leads a professional wrestling stable.

### PF-7 (medium)

All of Zaha Hadid's design styles are timeless. No mass product design is timeless. Either Zaha Hadid's design style or Kelly Wearstler's design style. All of Kelly Wearstler's design styles are evocative. All of Kelly Wearstler's design styles are dreamy. If a design by Max is timeless, then a design by Max is a mass product design and evocative. In conclusion: A design by Max is a mass product design.

### PF-8 (hard)

In superhero movies, the good guys always win. The Surprising Adventures of Sir Digby Chicken Caesar is a superhero movie. Good guys fight bad guys and vice versa. Sir Digby fights his nemesis. If a superhero movie is named after a character, that character is a good guy. The Surprising Adventures of Sir Digby Chicken Caesar is named after Sir Digby. If somebody wins a fight, the person they are fighting loses. If a superhero movie is named after a character, that character appears in the movie. In conclusion: Sir Digby’s nemesis loses.

### PF-9 (hard)

Pets are allowed in some managed buildings. A deposit is required to rent an apartment in a managed building. The security deposit can be either equal to one month's rent or more. Fluffy is Tom's cat. Cats are pets. The Olive Garden is a managed building. The monthly rent at the Olive Garden is $2000. Tom will rent an apartment in a managed building if and only if he is allowed to move in with Fluffy, and the security deposit is no more than $1500. 2000$ is more than $1500. In conclusion: Tom will rent an apartment in The Olive Garden.

### PF-10 (hard)

If a man is taller than another man, the taller one can block the other's shooting. Michael is a man who is taller than everyone else in his class. If person x is taller than person y, and person y is taller than person z, then x is taller than z. Peter is a man who is taller than Michael. Michael can block any shooting from a person as long as the person does not jump when shooting. Michael cannot block Windy's shooting. Every shooter who can jump when shooting is a great shooter. In conclusion: Peter is shorter than a man in Michael's class.
