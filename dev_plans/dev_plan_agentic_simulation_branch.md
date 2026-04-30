# Agentic simulation line — branch and commit rules

**Branch:** `agentic-simulation` (remote: `origin/agentic-simulation`).

**Scope:** Work for the upcoming “agentic simulation” track is developed **only** on this branch so `ClinCon-version`, `smt-pipeline`, `asp`, and `main` stay unchanged until you explicitly merge or cherry-pick elsewhere.

## Commit policy

- **Do not commit** unless the maintainer **explicitly** says to commit (e.g. “commit this”, “save to git”).
- When committing:
  1. Confirm current branch: `git branch --show-current` → must be `agentic-simulation`.
  2. If not, run: `git checkout agentic-simulation` and merge/rebase as needed before committing.
  3. Commit and push only this branch:  
     `git push origin agentic-simulation`

## Product / technical notes

- Feature-specific design and task lists for agentic simulation should be appended under **§ Implementation** (or linked plans) as work proceeds.
- Keep commits focused; prefer one logical change per commit when the maintainer requests a save.

## Implementation

- *(Fill in when work starts: goals, modules touched, acceptance checks.)*
