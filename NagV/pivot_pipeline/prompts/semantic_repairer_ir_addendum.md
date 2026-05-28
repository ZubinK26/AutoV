# Semantic Repairer_Piv — critic DRIFT handoff

## Scope

- Repair **only** findings in `handoff.findings` / `approved_finding_ids`.
- **Never** implement items in `ignored_finding_ids` or findings omitted from the handoff.
- Cross-rule wiring (aggregate gates, escalation/status, obligation vs enforcement) may be deferred to **CrossRepairer** when routing says so — do not broaden into a full-policy rewrite.

## Rule ids and policy size

- **Do not invent new `rule_id` values** unless compile absolutely requires (rare).
- Output **`rules`** must include **every** `rule_id` from the input payload (same count; one id each).
- **Only edit** rules listed in `focus_rule_ids`; return **stubs unchanged** for all other ids.

## `LOGICAL_IMPLICATION` triggers

- Condition trees: **`atom`**, **`varcmp`**, **`varprod_cmp`**, **`and`**, **`or`**, **`not` only**.
- **Never** nest `k_of_n` or other vNext templates inside `trigger_condition` / `required_condition`.
- Wire aggregate rules with **`atom`** conjuncts on existing boolean variables.

## Focused payload (`focus_rule_ids`)

- Full rule bodies only for `focus_rule_ids`; other rules are stubs (`_payload_stub: true`).
- Echo stubs **verbatim** in the output.

## change_summary

- Prefer `{ "finding_id": "C001", "rule_id": "R0036", "change": "..." }` when the critic handoff uses finding ids.
- One approved finding → minimal edits.

## `K_OF_N` (when in focus)

- Use optional **`result_variable`** for aggregate booleans; **never** top-level `variable` or `yields` on `K_OF_N` (stripped; repair validation fails).
- See `repairer_ir_normative.md` vNext section and `cross_repairer_ir_addendum.md` for wiring patterns.
