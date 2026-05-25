# Dev plan: GitHub branch with **only** pivot-relevant tree (cloneable & runnable)

**Status:** planning document — does not modify `main` by itself.  
**Goal:** A dedicated branch (or sibling repo) that contains **nothing unrelated** to running the **Pivot pipeline** end-to-end (scope rewriter → WFM → extract → meta-scheme → Z3 → optional gates), **without breaking** the full AutoV `main` workflow.

---

## 1. Non-negotiables

| Requirement | How we satisfy it |
|-------------|-------------------|
| `main` stays intact | Never delete paths on `main`. The slim branch is **published from** `main` via copy/sync or CI, not by manual pruning on `main`. |
| Clone + install + run on a fresh machine | **One** root `pyproject.toml`, **`pip install -e .`**, `.env` with `GEMINI_API_KEY` (see `.env.example`), documented minimal commands. |
| Nothing “un related” | Maintain an explicit **allowlist** of paths; reject everything else on the slim branch. |
| Verify | CI on the slim branch: `pip install -e .` + `pivot-pipeline --help` + targeted `pytest` (see §6). |

---

## 2. Canonical path allowlist (from current repo layout)

These packages are already wired in **root** [`pyproject.toml`](../pyproject.toml) (`tool.setuptools.packages` + `package-dir`):

| Path | Role |
|------|------|
| [`NagV/pivot_pipeline/`](../NagV/pivot_pipeline/) | CLI, IR, Z3, critic, template suite, scope rewriter CLI, etc. |
| [`NagV/pivot_wfm/`](../NagV/pivot_wfm/) | Phase 0 pivot WFM orchestration |
| [`wfm_orchestration/`](../wfm_orchestration/) | `parse_nl_rules` and related (imported by `pivot_pipeline.run`, `policy_gates`, `extract`) |
| [`registry_stage/`](../registry_stage/) | `registry_stage.llm.gemini_call` — Gemini + `load_repo_dotenv` (imported by `pivot_pipeline.cli`, `llm`, scope rewriter) |

**Docs (optional but useful on the slim branch)**

- [`NagV/Extract-Pivot.md`](../NagV/Extract-Pivot.md)
- [`NagV/pivot_pipeline/ARCHITECTURE.md`](../NagV/pivot_pipeline/ARCHITECTURE.md)
- [`NagV/pivot_pipeline/PIVOT_TEMPLATE_SYSTEM.md`](../NagV/pivot_pipeline/PIVOT_TEMPLATE_SYSTEM.md)
- [`NagV/pivot_pipeline/README.md`](../NagV/pivot_pipeline/README.md)
- [`NagV/demo-presentation-file.md`](../NagV/demo-presentation-file.md) (if you want demo narrative)

**Root files on slim branch**

- [`pyproject.toml`](../pyproject.toml) — adjust on slim branch only if you **trim** test paths or **add** missing runtime deps (§5).
- `.env.example` at **AutoV repo root** (same directory as `pyproject.toml`) — include on the slim branch so new clones know required env vars.
- **`README.md` (new, minimal)** — clone, `python -m venv`, `pip install -e .`, `.env`, example `pivot-pipeline` / `scope-rewriter` commands.

**Explicitly excluded** (examples): `CPMpy/`, `NagV/nagv/` (optional **except** if you later require `nagv.agent_trace`; current code treats it as optional import in `run.py`), `NagV/exports/`, large unrelated assets, etc.

---

## 3. Dependency audit (slim branch must be self-consistent)

Root `pyproject.toml` **today** lists `pydantic` and `z3-solver`. Runtime pivot + Gemini requires **at least**:

- `google-genai` (used by `registry_stage.llm.gemini_call`: `from google import genai`)
- `python-dotenv` (optional but needed for `load_repo_dotenv` to work as intended)

**Action:** On the **slim** branch (or before first publish), align `dependencies` in `pyproject.toml` with what a clean `pip install -e .` + minimal smoke run actually needs. Confirm with:

```text
pip install -e .
pivot-pipeline --help
```

then one **non-LLM** or **mocked** test path if available.

`pytest` can be a **dev** extra (`[project.optional-dependencies] dev = ["pytest", ...]`) so consumers can omit it.

---

## 4. Recommended delivery mechanism

### Option A — **Orphan branch `pivot-dist` in the same repo** (simple for one remote)

1. From automation, create an **orphan** branch (no shared history) or reset a long-lived `pivot-dist` branch **only** from generated tree (team choice).
2. Script or CI job:
   - Checkout `main` at SHA **X**
   - Copy allowlisted paths into a clean temp dir
   - Add minimal README + verified `pyproject.toml`
   - Commit with message `pivot-dist: sync from main <sha>`
   - Force-push **`pivot-dist`** (protected branch rules: allow this only for maintainers)

**Pros:** One remote URL; easy for others to `git clone -b pivot-dist`.  
**Cons:** `pivot-dist` history is **not** a normal continuation of `main` if you use orphan + force-push — document that consumers use **`main` for development**, **`pivot-dist` for handoff**.

### Option B — **Separate GitHub repo `AutoV-pivot`** (cleanest audience story)

- Same copy script; CI pushes to **other** repo PAT or deploy key.
- **Pros:** No confusion with monorepo branches; stars/releases only for pivot.
- **Cons:** Two repos to bump.

**Recommendation:** **Option B** for external demos; **Option A** for internal “one clone, two refnames”.

---

## 5. Automation checklist (one-time + recurring)

1. **Allowlist manifest** — version-controlled JSON/YAML listing directories + optional glob includes (e.g. `NagV/pivot_pipeline/prompts/*.md`).
2. **`scripts/sync_pivot_dist.py`** (or `Makefile` target):
   - Input: path to full AutoV clone, output: temp dir
   - Copy allowlist; fail if missing path
   - Optionally **strip** `__pycache__`, `.git` from staging only
3. **GitHub Action** (`workflow_dispatch` + on `push` to `main` optional):
   - Runs sync; commits to `pivot-dist` or pushes to sibling repo
4. **Branch protection:** `main` unchanged; `pivot-dist` may allow fast-forward-only or bot-only pushes.

---

## 6. CI gates on the slim artifact

Minimum:

- `python -m pip install -e .`
- `pivot-pipeline --help`
- `scope-rewriter --help` / `pivot-template-suite --help`
- `pytest NagV/pivot_pipeline/tests -q` (subset) and/or `NagV/pivot_wfm/tests` if packaged

Full LLM e2e **not** required in CI (needs secrets); optional nightly with `GEMINI_API_KEY` in repo secrets.

---

## 7. Safety: “don’t break main”

- All development continues on **`main`**. The slim branch is **generated**, never the source of truth for code edits.
- If you need to fix pivot, fix on **`main`**, then **re-sync** slim branch.

---

## 8. What the assistant / developer can do vs what you must do locally

| Who | Action |
|-----|--------|
| **In-repo (Cursor / dev)** | Add this plan; add `scripts/sync_pivot_dist.*` + allowlist; tighten slim `pyproject.toml` dependencies in the **generated** tree or maintain a `pyproject.pivot-dist.toml` template copied by sync; add minimal root README template; add GitHub Action YAML **if** you want automated publish. |
| **You (GitHub)** | Create **`pivot-dist`** branch first time (or create empty sibling repo), add **`GEMINI_API_KEY`** secret if CI runs LLM tests, configure branch protection, **paste PAT** or deploy key for cross-repo push **if** using Option B. |
| **Cannot be done without your GitHub auth** | First **`git push`** of new branch/repo, PAT creation, enabling Actions on fork/org policies. |

**Summary:** The plan is **fully specifiable and mostly implementable in the AutoV repo** (script + CI files + README template). **You** still perform the **first GitHub branch/repo creation and credential’d push** (or approve the Action that does so).

---

## 9. Ready / next step

This file is **`dev_plans/dev_plan_github_pivot_only_branch_v1.md`**.

**Next step (when executing):** implement §5 + §3, run sync locally into a temp dir, `pip install -e .` from temp dir, fix allowlist/declared deps until green, then push `pivot-dist` or sibling repo per §4.
