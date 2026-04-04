# WFM automated run — FOLIO examples (Agents 1 → 2 → 3), Gemini

**UTC timestamp:** 20260404_133907Z

## Contract (this run)

- **Model:** `gemini-3.1-pro-preview`
- **Temperature:** `0.0`
- **Max output tokens:** `16384`
- **Thinking level:** `LOW` (see `GEMINI_THINKING_LEVEL`; default is `low` for parity with non–extended-thinking Claude runs)
- **Compound operator limit (injected):** `8`
- **Agent 4:** skipped (no user disagreement simulation)

Full table: `test_sets/wfm_api_contract_gemini.md`

---

## F-1 (easy)

### Input

All squares have four sides. All four-sided things are shapes. In conclusion: All squares are shapes.

### Agent 1

Every square has exactly four sides. Every thing that has exactly four sides is a shape. In conclusion, every square is a shape.

### Agent 2

1. "Every square has exactly four sides."
2. "Every thing that has exactly four sides is a shape."
3. "In conclusion, every square is a shape."

### Agent 3

PASS: "Every square has exactly four sides."
REWRITE: "For every item, if the item has exactly four sides, then the item is a shape." | DIFF: Rephrased computed set ("Every thing that has...") into a conditional over a general domain. No substantive loss — wording only.
PASS: "In conclusion, every square is a shape."

---

## F-2 (easy)

### Input

All cats are mammals. Some pets are not mammals. In conclusion: No pets are cats.

### Agent 1

Every cat is a mammal. At least one pet is not a mammal. In conclusion: No pet is a cat.

### Agent 2

1. "Every cat is a mammal."
2. "At least one pet is not a mammal."
3. "In conclusion: No pet is a cat."

### Agent 3

PASS: 1. "Every cat is a mammal."
PASS: 2. "At least one pet is not a mammal."
REWRITE: 3. "No pet is a cat." | DIFF: Removed discourse marker "In conclusion:" to isolate the logical rule; no substantive loss.

---

## F-3 (easy)

### Input

All fir trees are evergreens. Some objects of worship are fir trees. In conclusion: Some evergreens are not objects of worship.

### Agent 1

Every fir tree is an evergreen. At least one object of worship is a fir tree. In conclusion: At least one evergreen is not an object of worship.

### Agent 2

1. "Every fir tree is an evergreen."
2. "At least one object of worship is a fir tree."
3. "At least one evergreen is not an object of worship."

### Agent 3

PASS: 1. "Every fir tree is an evergreen."
PASS: 2. "At least one object of worship is a fir tree."
PASS: 3. "At least one evergreen is not an object of worship."

---

## F-4 (medium)

### Input

If people perform in school talent shows often, then they attend and are very engaged with school events. People either perform in school talent shows often or are inactive and disinterested members of their community. If people chaperone high school dances, then they are not students who attend the school. All people who are inactive and disinterested members of their community chaperone high school dances. All young children and teenagers who wish to further their academic careers and educational opportunities are students who attend the school. Bonnie either both attends and is very engaged with school events and is a student who attends the school, or she neither attends and is very engaged with school events nor is a student who attends the school. In conclusion: Bonnie performs in school talent shows often.

### Agent 1

If a person performs in school talent shows often, then that person attends school events and is very engaged with school events. Every person either performs in school talent shows often or is an inactive and disinterested member of their community. If a person chaperones high school dances, then that person is not a student who attends the school. Every person who is an inactive and disinterested member of their community chaperones high school dances. Every young child who wishes to further their academic careers and educational opportunities and every teenager who wishes to further their academic careers and educational opportunities is a student who attends the school. Bonnie either both attends school events and is very engaged with school events and is a student who attends the school, or Bonnie neither attends school events and is very engaged with school events nor is a student who attends the school. In conclusion: Bonnie performs in school talent shows often.

### Agent 2

1. "If a person performs in school talent shows often, then that person attends school events."
2. "If a person performs in school talent shows often, then that person is very engaged with school events."
3. "Every person either performs in school talent shows often or is an inactive and disinterested member of their community."
4. "If a person chaperones high school dances, then that person is not a student who attends the school."
5. "Every person who is an inactive and disinterested member of their community chaperones high school dances."
6. "Every young child who wishes to further their academic careers and educational opportunities is a student who attends the school."
7. "Every teenager who wishes to further their academic careers and educational opportunities is a student who attends the school."
8. "Bonnie either both attends school events and is very engaged with school events and is a student who attends the school, or Bonnie neither attends school events and is very engaged with school events nor is a student who attends the school."
9. "Bonnie performs in school talent shows often."

### Agent 3

PASS: 1. "If a person performs in school talent shows often, then that person attends school events."
PASS: 2. "If a person performs in school talent shows often, then that person is very engaged with school events."
PASS: 3. "Every person either performs in school talent shows often or is an inactive and disinterested member of their community."
PASS: 4. "If a person chaperones high school dances, then that person is not a student who attends the school."
PASS: 5. "Every person who is an inactive and disinterested member of their community chaperones high school dances."
PASS: 6. "Every young child who wishes to further their academic careers and educational opportunities is a student who attends the school."
PASS: 7. "Every teenager who wishes to further their academic careers and educational opportunities is a student who attends the school."
PASS: 8. "Bonnie either both attends school events and is very engaged with school events and is a student who attends the school, or Bonnie neither attends school events and is very engaged with school events nor is a student who attends the school."
PASS: 9. "Bonnie performs in school talent shows often."

---

## F-5 (medium)

### Input

Monkeypox is an infectious disease caused by the monkeypox virus. Monkeypox virus can occur in certain animals, including humans. Humans are mammals. Mammals are animals. Symptons of Monkeypox include fever, headache, muscle pains, feeling tired, and so on. People feel tired when they get the flu. In conclusion: There is an animal.

### Agent 1

Monkeypox is an infectious disease caused by the monkeypox virus. 
The monkeypox virus can occur in certain animals, including humans. 
Every human is a mammal. 
Every mammal is an animal. 
Symptoms of Monkeypox include fever, headache, muscle pains, feeling tired, and other symptoms. 
Every person feels tired when that person gets the flu. 
In conclusion: There is at least one animal.

### Agent 2

1. "Monkeypox is an infectious disease caused by the monkeypox virus."
2. "The monkeypox virus can occur in certain animals, including humans."
3. "Every human is a mammal."
4. "Every mammal is an animal."
5. "Symptoms of Monkeypox include fever."
6. "Symptoms of Monkeypox include headache."
7. "Symptoms of Monkeypox include muscle pains."
8. "Symptoms of Monkeypox include feeling tired."
9. "Symptoms of Monkeypox include other symptoms."
10. "Every person feels tired when that person gets the flu."
11. "In conclusion: There is at least one animal."

### Agent 3

PASS: 1. "Monkeypox is an infectious disease caused by the monkeypox virus."
PASS: 2. "The monkeypox virus can occur in certain animals, including humans."
PASS: 3. "Every human is a mammal."
PASS: 4. "Every mammal is an animal."
PASS: 5. "Symptoms of Monkeypox include fever."
PASS: 6. "Symptoms of Monkeypox include headache."
PASS: 7. "Symptoms of Monkeypox include muscle pains."
PASS: 8. "Symptoms of Monkeypox include feeling tired."
PASS: 9. "Symptoms of Monkeypox include other symptoms."
PASS: 10. "Every person feels tired when that person gets the flu."
PASS: 11. "In conclusion: There is at least one animal."

---

## F-6 (medium)

### Input

There are six types of wild turkeys: Eastern wild turkey, Osceola wild turkey, Gould’s wild turkey, Merriam’s wild turkey, Rio Grande wild turkey, and Ocellated wild turkey. Tom is not an Eastern wild turkey. Tom is not an Osceola wild turkey. Tom is also not a Gould's wild turkey, or a Merriam's wild turkey, or a Rio Grande wild turkey. Tom is a wild turkey. In conclusion: Tom is an Ocellated wild turkey.

### Agent 1

There are exactly six types of wild turkeys: the Eastern wild turkey, the Osceola wild turkey, the Gould’s wild turkey, the Merriam’s wild turkey, the Rio Grande wild turkey, and the Ocellated wild turkey. Tom is a wild turkey. Tom is not an Eastern wild turkey. Tom is not an Osceola wild turkey. Tom is not a Gould's wild turkey. Tom is not a Merriam's wild turkey. Tom is not a Rio Grande wild turkey. Therefore, Tom is an Ocellated wild turkey.

### Agent 2

1. "There are exactly six types of wild turkeys: the Eastern wild turkey, the Osceola wild turkey, the Gould’s wild turkey, the Merriam’s wild turkey, the Rio Grande wild turkey, and the Ocellated wild turkey."
2. "Tom is a wild turkey."
3. "Tom is not an Eastern wild turkey."
4. "Tom is not an Osceola wild turkey."
5. "Tom is not a Gould's wild turkey."
6. "Tom is not a Merriam's wild turkey."
7. "Tom is not a Rio Grande wild turkey."
8. "Therefore, Tom is an Ocellated wild turkey."

### Agent 3

PASS: 1. "There are exactly six types of wild turkeys: the Eastern wild turkey, the Osceola wild turkey, the Gould’s wild turkey, the Merriam’s wild turkey, the Rio Grande wild turkey, and the Ocellated wild turkey."
PASS: 2. "Tom is a wild turkey."
PASS: 3. "Tom is not an Eastern wild turkey."
PASS: 4. "Tom is not an Osceola wild turkey."
PASS: 5. "Tom is not a Gould's wild turkey."
PASS: 6. "Tom is not a Merriam's wild turkey."
PASS: 7. "Tom is not a Rio Grande wild turkey."
REWRITE: 8. "Tom is an Ocellated wild turkey." | DIFF: No substantive loss — wording only; removed the discourse marker "Therefore" to state the property assignment directly.

---

## F-7 (medium)

### Input

A Japanese game company created the game the Legend of Zelda. All games in the Top 10 list are made by Japanese game companies. If a game sells more than one million copies, then it will be selected into the Top 10 list. The Legend of Zelda sold more than one million copies. In conclusion: The Legend of Zelda is in the Top 10 list.

### Agent 1

A Japanese game company created the game The Legend of Zelda. 
Every game in the Top 10 list is created by a Japanese game company. 
If a game sells more than one million copies, then the game is in the Top 10 list. 
The game The Legend of Zelda sold more than one million copies. 
In conclusion: The game The Legend of Zelda is in the Top 10 list.

### Agent 2

1. "A Japanese game company created the game The Legend of Zelda."
2. "Every game in the Top 10 list is created by a Japanese game company."
3. "If a game sells more than one million copies, then the game is in the Top 10 list."
4. "The game The Legend of Zelda sold more than one million copies."
5. "The game The Legend of Zelda is in the Top 10 list."

### Agent 3

PASS: 1. "A Japanese game company created the game The Legend of Zelda."
PASS: 2. "Every game in the Top 10 list is created by a Japanese game company."
PASS: 3. "If a game sells more than one million copies, then the game is in the Top 10 list."
PASS: 4. "The game The Legend of Zelda sold more than one million copies."
PASS: 5. "The game The Legend of Zelda is in the Top 10 list."

---

## F-8 (hard)

### Input

All employees who schedule a meeting with their customers will appear in the company today. Everyone who has lunch in the company schedules meetings with their customers. Employees will either have lunch in the company or have lunch at home. If an employee has lunch at home, then he/she is working remotely from home. All employees who are in other countries work remotely from home. No managers work remotely from home. James is either a manager and appears in the company today or neither a manager nor appears in the company today. In conclusion: James has lunch in the company.

### Agent 1

Every employee who schedules a meeting with their customers appears in the company today. 
Every employee who has lunch in the company schedules a meeting with their customers. 
Every employee either has lunch in the company or has lunch at home. 
If an employee has lunch at home, then that employee works remotely from home. 
Every employee who is in another country works remotely from home. 
No manager works remotely from home. 
James is either a manager who appears in the company today, or James is neither a manager nor appears in the company today. 
In conclusion: James has lunch in the company.

### Agent 2

1. "Every employee who schedules a meeting with their customers appears in the company today."
2. "Every employee who has lunch in the company schedules a meeting with their customers."
3. "Every employee either has lunch in the company or has lunch at home."
4. "If an employee has lunch at home, then that employee works remotely from home."
5. "Every employee who is in another country works remotely from home."
6. "No manager works remotely from home."
7. "James is either a manager who appears in the company today, or James is neither a manager nor appears in the company today."
8. "In conclusion: James has lunch in the company."

### Agent 3

REWRITE: For every employee, if the employee schedules a meeting with their customers, then the employee appears in the company today. | DIFF: Rephrased computed set into a universal quantifier with an implication; no substantive loss.
REWRITE: For every employee, if the employee has lunch in the company, then the employee schedules a meeting with their customers. | DIFF: Rephrased computed set into a universal quantifier with an implication; no substantive loss.
PASS: 3. "Every employee either has lunch in the company or has lunch at home."
REWRITE: For every employee, if the employee has lunch at home, then the employee works remotely from home. | DIFF: Rephrased "an employee" to explicit universal quantifier; no substantive loss.
REWRITE: For every employee, if the employee is in another country, then the employee works remotely from home. | DIFF: Rephrased computed set into a universal quantifier with an implication; no substantive loss.
REWRITE: For every manager, it is not the case that the manager works remotely from home. | DIFF: Rephrased "No manager" to explicit universal quantifier with negation; no substantive loss.
PASS: 7. "James is either a manager who appears in the company today, or James is neither a manager nor appears in the company today."
PASS: 8. "In conclusion: James has lunch in the company."

---

## F-9 (hard)

### Input

A person is either a Grand Slam champion or an Oscar-nominated actor. All people who are Grand Slam champions are professional tennis players. All Oscar-nominated actors are celebrities. All professional tennis players are athletes. If a person is a celebrity then they are well paid. If a person is an athlete then they are famous. All well-paid people live in tax havens. If Djokovic is famous and is an athlete, then Djokovic lives in a tax haven. In conclusion: Djokovic is a Grand Slam champion.

### Agent 1

Every person is either a Grand Slam champion or an Oscar-nominated actor. 
Every person who is a Grand Slam champion is a professional tennis player. 
Every Oscar-nominated actor is a celebrity. 
Every professional tennis player is an athlete. 
If a person is a celebrity, then that person is well-paid. 
If a person is an athlete, then that person is famous. 
Every well-paid person lives in a tax haven. 
If Djokovic is famous and Djokovic is an athlete, then Djokovic lives in a tax haven. 
In conclusion: Djokovic is a Grand Slam champion.

### Agent 2

1. "Every person is either a Grand Slam champion or an Oscar-nominated actor."
2. "Every person who is a Grand Slam champion is a professional tennis player."
3. "Every Oscar-nominated actor is a celebrity."
4. "Every professional tennis player is an athlete."
5. "If a person is a celebrity, then that person is well-paid."
6. "If a person is an athlete, then that person is famous."
7. "Every well-paid person lives in a tax haven."
8. "If Djokovic is famous and Djokovic is an athlete, then Djokovic lives in a tax haven."
9. "In conclusion: Djokovic is a Grand Slam champion."

### Agent 3

PASS: 1. "Every person is either a Grand Slam champion or an Oscar-nominated actor."
REWRITE: 2. "For every person, if the person is a Grand Slam champion, then the person is a professional tennis player." | DIFF: Rephrased computed set into an explicit conditional over the domain of persons. No substantive loss.
REWRITE: 3. "For every person, if the person is an Oscar-nominated actor, then the person is a celebrity." | DIFF: Rephrased computed set into an explicit conditional over the domain of persons. No substantive loss.
REWRITE: 4. "For every person, if the person is a professional tennis player, then the person is an athlete." | DIFF: Rephrased computed set into an explicit conditional over the domain of persons. No substantive loss.
REWRITE: 5. "For every person, if the person is a celebrity, then the person is well-paid." | DIFF: Made the universal quantification over persons explicit. No substantive loss.
REWRITE: 6. "For every person, if the person is an athlete, then the person is famous." | DIFF: Made the universal quantification over persons explicit. No substantive loss.
REWRITE: 7. "For every person, if the person is well-paid, then the person lives in a tax haven." | DIFF: Rephrased computed set into an explicit conditional over the domain of persons. No substantive loss.
PASS: 8. "If Djokovic is famous and Djokovic is an athlete, then Djokovic lives in a tax haven."
REWRITE: 9. "Djokovic is a Grand Slam champion." | DIFF: Removed the rhetorical "In conclusion:" prefix to leave just the logical proposition. No substantive loss.

---

## F-10 (hard)

### Input

Symphony No. 9 is a music piece. Composers write music pieces. Beethoven wrote Symphony No. 9. Vienna Music Society premiered Symphony No. 9. Vienna Music Society is an orchestra. Beethoven leads the Vienna Music Society. Orchestras are led by conductors. In conclusion: Beethoven is a composer.

### Agent 1

Symphony No. 9 is a music piece.
Every composer writes at least one music piece.
Beethoven wrote Symphony No. 9.
The Vienna Music Society premiered Symphony No. 9.
The Vienna Music Society is an orchestra.
Beethoven leads the Vienna Music Society.
Every orchestra is led by at least one conductor.
In conclusion: Beethoven is a composer.

### Agent 2

1. "Symphony No. 9 is a music piece."
2. "Every composer writes at least one music piece."
3. "Beethoven wrote Symphony No. 9."
4. "The Vienna Music Society premiered Symphony No. 9."
5. "The Vienna Music Society is an orchestra."
6. "Beethoven leads the Vienna Music Society."
7. "Every orchestra is led by at least one conductor."
8. "In conclusion: Beethoven is a composer."

### Agent 3

PASS: 1. "Symphony No. 9 is a music piece."
PASS: 2. "Every composer writes at least one music piece."
PASS: 3. "Beethoven wrote Symphony No. 9."
PASS: 4. "The Vienna Music Society premiered Symphony No. 9."
PASS: 5. "The Vienna Music Society is an orchestra."
PASS: 6. "Beethoven leads the Vienna Music Society."
PASS: 7. "Every orchestra is led by at least one conductor."
REWRITE: 8. "Beethoven is a composer." | DIFF: Removed discourse marker "In conclusion:" with no substantive loss.

---
