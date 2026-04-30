# Gemini API contract — WFM FOLIO smoke runner

Aligned with **`wfm_api_contract_frozen.md`** (Claude) on sampling and limits so runs are comparable. Implemented by **`scripts/run_wfm_folio_gemini.py`** unless overridden by environment variables.

| Parameter | Default | Env override | Notes |
|-----------|---------|--------------|--------|
| **Provider** | Google AI Gemini API (`google-genai` SDK) | — | Same prompts and message choreography as the Claude runner. |
| **Model** | `gemini-3.1-pro-preview` | `GEMINI_MODEL` | Preview id as of Google’s model table; update when GA id ships. |
| **Temperature** | `0.0` | `GEMINI_TEMPERATURE` | Matches Claude frozen default. |
| **Max output tokens** | `16384` | `GEMINI_MAX_OUTPUT_TOKENS` | Same cap as Claude runner; Gemini 3.1 allows higher if you override. |
| **Top‑P / Top‑K** | *(unset — API defaults)* | — | Matches “leave at default” on Claude. |
| **Thinking** | `thinking_level=LOW` | `GEMINI_THINKING_LEVEL` | Gemini 3.x defaults to high reasoning depth if omitted. **`minimal` is not supported on Gemini 3.1 Pro** per Google docs; **`low`** is the supported setting closest to “no extra thinking” / parity with vanilla Claude (no extended-thinking block). Set to `unspecified` or `api_default` to omit `ThinkingConfig` entirely (API default, typically high on Gemini 3). |
| **System prompt** | Same fenced blocks as Claude runner | — | From `asp/wfm/prompts/agent_*.md`. |
| **User layout** | Agent 1: FOLIO text; 2: A1 out; 3: A2 out | — | Same as Claude runner. |
| **Agent 4** | Not called | — | — |
| **Compound operator limit** | `asp/wfm/config/wfm.json` | — | Injected into Agent 2 only. |

**Authentication:** `GEMINI_API_KEY` (required for non–dry-run). Put it in **`AutoV/.env`** next to `asp/wfm/` and `test_sets/` (see **`.env.example`**). **Never commit `.env`.**

**Usage logging:** JSONL rows include `usage.input_tokens` / `usage.output_tokens` from the API (`prompt_token_count` / `candidates_token_count`) and `usage.thoughts_tokens` when the API reports thought tokens.

**Run:**

```powershell
pip install -r test_sets/requirements-wfm-test.txt
python test_sets/scripts/run_wfm_folio_gemini.py --dry-run
python test_sets/scripts/run_wfm_folio_gemini.py
```
