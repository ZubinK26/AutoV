# WFM → CPMpy domain bundle

Structural mapping only: no product-specific NL interpretation beyond extracting `lines[].statement_nl`.

- **Input:** Registry-style handoff JSON (`schema_version`, `lines` with `statement_nl`, optional `agent3_verdict`).
- **Output:** `rules.txt` (one line per selected NL statement) and a **stub** `tools.json` (gated `apply_refund`). You must still add `signature.py` and `glossary.md` (or copy from a template domain).

Python API: `materialize_domain_bundle_from_handoff` in `adapter.py`.

CLI: `cpmpy-policy-pipeline prepare-from-wfm --handoff path.json --out-dir work/ext_bundle/`.
