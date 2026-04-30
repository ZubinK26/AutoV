# Frozen API contract — WFM FOLIO smoke runner

These values are what `scripts/run_wfm_folio_claude.py` uses unless overridden by environment variables. **Change this file when you intentionally change the contract**, and keep the script defaults in sync.

| Parameter | Frozen default | Env override | Notes |
|-----------|----------------|--------------|--------|
| **Provider** | Anthropic Messages API | — | HTTPS; not browser/chat UI. |
| **Model** | `claude-sonnet-4-20250514` | `ANTHROPIC_MODEL` | Sonnet 4. Use `claude-3-5-sonnet-20241022` etc. if your key targets a different id. |
| **Temperature** | `0.0` | `ANTHROPIC_TEMPERATURE` | Zero for reproducibility. |
| **Max output tokens** | `16384` | `ANTHROPIC_MAX_TOKENS` | Large enough for long Agent 2/3 outputs. |
| **Top‑P** | *(unset — API default)* | — | Anthropic defaults apply unless you extend the script. |
| **System prompt** | Full fenced block from each `asp/wfm/prompts/agent_*.md` | — | Verbatim extraction between the first pair of ` ``` ` fences after the title. |
| **User role layout** | Agent 1: raw FOLIO example text only. Agent 2: Agent 1 output only. Agent 3: Agent 2 output only. | — | No extra wrapper text unless you edit the script. |
| **Agent 4** | **Not called** | — | UI/handler path omitted in this runner. |
| **Compound operator limit** | Read from `asp/wfm/config/wfm.json` → `compound_operator_limit` | — | Injected into Agent 2 system text (replaces limit/budget integers so config matches the model). |

**Authentication:** `ANTHROPIC_API_KEY` (required for non–dry-run). Prefer a **`.env`** file in the repo root next to `asp/wfm/` and `test_sets/`: copy **`.env.example`** → `.env`, add your key. **`.env` is in `.gitignore`** — never commit it or use `git add -f .env`.

**Reproducibility:** Even with `temperature=0`, minor variance across API versions or routing can occur. Log the **exact** model id and the **git commit** (optional) with each report.
