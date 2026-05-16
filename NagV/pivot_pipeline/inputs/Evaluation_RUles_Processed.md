Local repositories must be updated, at a minimum via a fetch and prune operation, before any evaluation begins. 

The full repository evidence must be evaluated in a strictly prioritized order: first the main branch as the default expectation, second any other branches, and third any pull requests or PR branches. 

If the best valid implementation is not located on the main branch, the final evaluation must be based exclusively on the specific branch or pull request that contains the most complete, task-relevant deliverables.

Grades must be assigned on a per-task and per-student basis, including for group repositories. 

The standard baseline maximum score for a task is 10.0 points. Certain tasks allow bonus points. 

Bonus points must be awarded only if the baseline score equals exactly 10.0 points, signifying that the base task requirements were fully met. 

If a penalty rule applies, it strictly overrides any bonus points.



---

The evaluation must strictly follow the official task specification for the given week or task. 

If a task receives partial points for partial completion, the missing core elements must be explicitly listed. 

Any generated feedback reports must explicitly contain concrete gaps, specifically detailing what is missing, where it should be, and what evidence was expected. 

The language used in all feedback reports must be English.

If the evaluation concerns Task 04 and the report does not clearly separate earlier-task samples, such as acquisition or schema fixtures, from Task 04 pipeline outputs, such as cleaned, joined, or aggregated samples, EDA exports, and full output locations, then a note explicitly referencing Task 04 spec section 4.1.1 must be generated.



---

The team size must equal the count of unique student identifier tokens present in the repository name. 

If the base score is less than 10.0, the total bonus points applied must equal 0.0. 

If any bonus points are applied, the base score must equal exactly 10.0. 

If the base score equals 10.0 and the team size is exactly one person, an additional 0.5 bonus points must be applied. 

If the base score equals 10.0 and the requirements intended for a team one size larger are fully met, an additional 0.5 bonus points must be applied. 

If the base score equals 10.0 and the four-person tier requirements are fully met, an additional 1.0 bonus point must be applied. 

The total cumulative bonus points must be less than or equal to 2.0. 

If the team size is one person, the total score must be less than or equal to 12.0. 

If the team size is two persons, the total score must be less than or equal to 11.5. 

If the team size is three persons, the total score must be less than or equal to 11.0. 

If the team size is four persons, the total score must be less than or equal to 10.0.

---

The calculation of the contribution split must be based exclusively on code files, explicitly excluding markdown files and data files. 

If the total number of task-specific code lines is less than 30, contribution split penalties must be skipped for that specific task. 

The default basis for calculating the split is the task-specific code scope. 

As a fairness fallback, if the task-specific split is strongly one-sided, the whole-repository code split must also be checked before a penalty is applied. 

If a student's contribution share is less than 0.25, an imbalance penalty may be applied on a case-by-case basis, and if applied, it must be documented. 

If a student's contribution share is less than 0.05, that student must receive a final score of exactly 0 points, their teammate must receive a 2-point penalty, the teammate is forbidden from keeping any bonus points, and this specific decision must be explicitly documented in the feedback.

---

If the specification requires GitHub Project evidence based on team size, the following elements must be evaluated: whether the project exists and is correctly mapped to the specific course task, whether the acceptance criteria are concrete, whether ownership requirements are met when a "one per person" rule applies, and whether there is valid traceability linking tasks or issues to repository work such as commits, branches, or pull requests. 

A point reduction penalty for poor-quality project tasks must be applied if and only if the specification explicitly requires Project evidence.

---

Branch names must be descriptive and task-related, explicitly avoiding arbitrary names such as test, new, or asd. 

Commit messages must be meaningful and consistent, with a preference for the imperative mood. 

The committing of large datasets must be avoided. 

For teamwork, the use of pull requests and code reviews is considered a plus, and force-pushes to shared branches must be avoided.

---

The language used for all feedback notes must be English. 

A feedback markdown file must be generated if the student's score is less than 10.0. 

A feedback markdown file must also be generated if a special policy note, such as a contribution penalty, is required, regardless of the final score. 

The content of the feedback file must focus explicitly on missing core deliverables and serious gaps, excluding minor style issues.

---

For each evaluated task, a corresponding task-specific directory must exist under the wyniki/ folder. Within this task directory, the group-specific results CSV files must be present. 

If student feedback reports are required by previous evaluation rules, a reports_md/ subdirectory must exist and be populated with those specific reports. 

An optional repository-level audit CSV file, containing data such as the evaluated branch, commit hash, points breakdown, and code-line counts, is permitted to exist within the task folder.
