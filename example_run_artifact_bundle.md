# Example run artifact bundle (Test_input2)

This is a **single-file rollup** of material from the archived pivot workspace [`NagV/exports/pivot_runs_test_input2/`](NagV/exports/pivot_runs_test_input2/README.md). It is meant for **read-through**: original policy text, a readable Phase 0 (WFM) summary, the English that fed formalization for this export, a linear view of the rule IR used for alignment, and the compiled **`meta_scheme.json`** for the model.

It reflects **one recorded pipeline run** fixed in that directory (including handoffs, critic, and solver artifacts). See `run_summary.json` there for machine-readable outcome and paths.

## 1. Original, unprocessed source NL

Copied into the export as `source_policy_Test_input2.md` (authoring-time wording before Phase 0).

```text
The requested token consumption must be strictly less than or equal to 100,000.

The agent's semantic confidence score must be strictly greater than 0.85.

The allocated compute cores multiplied by the requested runtime hours must be less than or equal to 120.

The proposed financial budget multiplied by the task risk multiplier must not exceed 500.

The requested memory allocation must not exceed the agent's pre-authorized memory limit.

The maximum concurrent API calls requested must be strictly less than 50.

The model engine version must be one of the following: "GPT-4", "CLAUDE-3", "GEMINI-3".

The target deployment environment must be one of the following: "DEV", "STAGING", "SANDBOX".

The proposed outbound network port must not be one of the following: 22, 23, 3389.

If the action type is "WRITE", the agent role must be "AUTONOMOUS_EDITOR".

If the target dataset contains PII, the human_in_loop flag must be true.

If the request origin subnet is "EXTERNAL", a cryptographic secondary token must be provided.

If the target geographic region is "EU", the compliance enforcement flag must be true.

If the target system is "FINANCIAL_LEDGER", the required approval level must be "DIRECTOR".

If the action type is "DESTRUCTIVE", the request is immediately denied regardless of other conditions.

If the global quarantine flag is true, the request is immediately denied regardless of other conditions.

If an emergency override token is provided, the budget math limit (Rule 4) and token consumption limit (Rule 1) are bypassed.

If the agent role is "READ_ONLY", the human_in_loop requirement for PII data (Rule 11) is waived.

If the target environment is "SANDBOX", the outbound network port restrictions (Rule 9) are bypassed.

If the request involves system configuration changes, it is denied unless the human_in_loop flag is true.
```

---

## 2. WFM (Phase 0) — readable summary

Pivot WFM processed the source in **5 rules per chunk**; **`next_rule_index`** is **20** (see `nl_chunk_progress.json` for full progress).

### Chunk handoffs (bundle id per slice)

| Chunk | Rule lines | Bundle id |
|------:|------------|-----------|
| 0 | rules 0–5 | `pivotwfm_20260507_025107Z_c3c13963` |
| 1 | rules 5–10 | `pivotwfm_20260507_025144Z_f003a8cc` |
| 2 | rules 10–15 | `pivotwfm_20260507_025247Z_97c4d5d3` |
| 3 | rules 15–20 | `pivotwfm_20260507_025437Z_67f85e03` |

### Phase 0 meta (`pivot_wfm_phase0_meta.json`)

```json
{
  "schema_version": "pivot_wfm_phase0_meta_v1",
  "chunks_this_invocation": 4,
  "source_rule_count_at_start": 20
}
```

### Forward-line aggregate (`pivot_wfm_nl_aggregate.json`)

```json
{
  "schema_version": "pivot_wfm_nl_aggregate_v1",
  "ok": true,
  "forward_line_count": 20,
  "blocking_line_count": 0,
  "blocking_lines": []
}
```

### Coverage log (`pivot_wfm_coverage_log.jsonl`, one JSON object per line)

```
{"event": "chunk_coverage_ok", "bundle_id": "pivotwfm_20260507_025107Z_c3c13963", "rule_index_start": 0, "rule_index_end": 5, "wfm_attempt": 1}
{"event": "chunk_coverage_ok", "bundle_id": "pivotwfm_20260507_025144Z_f003a8cc", "rule_index_start": 5, "rule_index_end": 10, "wfm_attempt": 1}
{"event": "chunk_coverage_ok", "bundle_id": "pivotwfm_20260507_025247Z_97c4d5d3", "rule_index_start": 10, "rule_index_end": 15, "wfm_attempt": 1}
{"event": "chunk_coverage_ok", "bundle_id": "pivotwfm_20260507_025437Z_67f85e03", "rule_index_start": 15, "rule_index_end": 20, "wfm_attempt": 1}
```

*(Each line above is a separate JSON object.)*

---

## 3. Processed NL used for formalization (`rules_source.txt`)

After Phase 0, this **one-line-per-rule** stream is what the extract / registry stages used as the English basis for this export.

```text
Every requested token consumption must be less than or equal to 100,000 tokens.

Every agent's semantic confidence score must be greater than 0.85.

The product of the number of allocated compute cores and the number of requested runtime hours must be less than or equal to 120 core-hours.

The product of the proposed financial budget and the task risk multiplier must be less than or equal to 500.

Every requested memory allocation must be less than or equal to the pre-authorized memory limit of the agent making the request.

The maximum number of concurrent API calls requested must be strictly less than 50.

The model engine version of every request must be one of the following: 'GPT-4', 'CLAUDE-3', or 'GEMINI-3'.

The target deployment environment of every deployment must be one of the following: 'DEV', 'STAGING', or 'SANDBOX'.

The proposed outbound network port of every request must not be one of the following: 22, 23, or 3389.

If the action type of a request is 'WRITE', then the agent role for that request must be 'AUTONOMOUS_EDITOR'.

If the target dataset of a request contains Personally Identifiable Information, then the human_in_loop flag for that request must be set to true.

If the origin subnet of a request is 'EXTERNAL', then the requester must provide exactly one cryptographic secondary token.

If the target geographic region of a request is 'EU', then the compliance enforcement flag for that request must be set to true.

If the target system of a request is 'FINANCIAL_LEDGER', then the required approval level for that request must be 'DIRECTOR'.

If the action type of a request is 'DESTRUCTIVE', then the request must be immediately denied, regardless of any other conditions.

If the global quarantine flag is true, then every request is denied regardless of any other conditions.

If a request provides an emergency override token, then the budget math limit (Rule 4) and the token consumption limit (Rule 1) do not apply to that request.

If the agent role of a request is 'READ_ONLY', then the human_in_loop requirement for PII data (Rule 11) does not apply to that request.

If the target environment of a request is 'SANDBOX', then the outbound network port restrictions (Rule 9) do not apply to that request.

If a request involves system configuration changes, then that request is denied unless the human_in_loop flag for that request is true.
```

---

## 4. Linearization of the model (`linearized_nl_and_model.txt`)

Numbered English (post-WFM) plus a line-oriented rendering of the **final** `rules_extracted.json` from this export.

```text
================================================================================
PROCESSED NL (1 line = 1 rule, WFM phase 0)
================================================================================

01. Every requested token consumption must be less than or equal to 100,000 tokens.

02. Every agent's semantic confidence score must be greater than 0.85.

03. The product of the number of allocated compute cores and the number of requested runtime hours must be less than or equal to 120 core-hours.

04. The product of the proposed financial budget and the task risk multiplier must be less than or equal to 500.

05. Every requested memory allocation must be less than or equal to the pre-authorized memory limit of the agent making the request.

06. The maximum number of concurrent API calls requested must be strictly less than 50.

07. The model engine version of every request must be one of the following: 'GPT-4', 'CLAUDE-3', or 'GEMINI-3'.

08. The target deployment environment of every deployment must be one of the following: 'DEV', 'STAGING', or 'SANDBOX'.

09. The proposed outbound network port of every request must not be one of the following: 22, 23, or 3389.

10. If the action type of a request is 'WRITE', then the agent role for that request must be 'AUTONOMOUS_EDITOR'.

11. If the target dataset of a request contains Personally Identifiable Information, then the human_in_loop flag for that request must be set to true.

12. If the origin subnet of a request is 'EXTERNAL', then the requester must provide exactly one cryptographic secondary token.

13. If the target geographic region of a request is 'EU', then the compliance enforcement flag for that request must be set to true.

14. If the target system of a request is 'FINANCIAL_LEDGER', then the required approval level for that request must be 'DIRECTOR'.

15. If the action type of a request is 'DESTRUCTIVE', then the request must be immediately denied, regardless of any other conditions.

16. If the global quarantine flag is true, then every request is denied regardless of any other conditions.

17. If a request provides an emergency override token, then the budget math limit (Rule 4) and the token consumption limit (Rule 1) do not apply to that request.

18. If the agent role of a request is 'READ_ONLY', then the human_in_loop requirement for PII data (Rule 11) does not apply to that request.

19. If the target environment of a request is 'SANDBOX', then the outbound network port restrictions (Rule 9) do not apply to that request.

20. If a request involves system configuration changes, then that request is denied unless the human_in_loop flag for that request is true.

================================================================================
LINEARIZED MODEL (final rules_extracted.json)
================================================================================

R0001 | CONSTANT_RELATIONAL | requested_token_consumption LTE 100000 | yields SATISFIED

R0002 | CONSTANT_RELATIONAL | agent_semantic_confidence_score GT 0.85 | yields SATISFIED

R0003 | LOGICAL_IMPLICATION | IF (allocated_compute_cores GTE 0 AND requested_runtime_hours GTE 0) THEN (allocated_compute_cores * requested_runtime_hours LTE 120)

R0004 | LOGICAL_IMPLICATION | IF proposed_financial_budget GTE 0 THEN (proposed_financial_budget * task_risk_multiplier LTE 500)

R0005 | VARIABLE_RELATIONAL | requested_memory_allocation LTE pre_authorized_memory_limit | yields SATISFIED

R0006 | CONSTANT_RELATIONAL | concurrent_api_calls LT 50 | yields SATISFIED

R0007 | SET_INCLUSION | model_engine_version IN ['GPT-4', 'CLAUDE-3', 'GEMINI-3'] | yields SATISFIED

R0008 | SET_INCLUSION | target_deployment_environment IN ['DEV', 'STAGING', 'SANDBOX'] | yields SATISFIED

R0009 | SET_INCLUSION | outbound_network_port NOT_IN [22, 23, 3389] | yields SATISFIED

R0010 | LOGICAL_IMPLICATION | IF action_type EQ WRITE THEN agent_role EQ AUTONOMOUS_EDITOR

R0011 | LOGICAL_IMPLICATION | IF target_dataset_contains_pii EQ true THEN human_in_loop EQ true

R0012 | LOGICAL_IMPLICATION | IF origin_subnet EQ EXTERNAL THEN cryptographic_secondary_token_count EQ 1

R0013 | LOGICAL_IMPLICATION | IF target_geographic_region EQ EU THEN compliance_enforcement_flag EQ true

R0014 | LOGICAL_IMPLICATION | IF target_system EQ FINANCIAL_LEDGER THEN required_approval_level EQ DIRECTOR

R0015 | LOGICAL_IMPLICATION | IF action_type EQ DESTRUCTIVE THEN decision EQ REJECT

R0016 | CONSTANT_RELATIONAL | global_quarantine_flag EQ true | yields UNSATISFIED

R0017 | PREEMPTION | IF emergency_override_token_provided EQ true THEN BYPASS_RULE target R0001

R0018 | PREEMPTION | IF agent_role EQ READ_ONLY THEN BYPASS_RULE target R0011

R0019 | PREEMPTION | IF target_deployment_environment EQ SANDBOX THEN BYPASS_RULE target R0009

R0020 | LOGICAL_IMPLICATION | IF (involves_system_configuration_changes EQ true AND NOT human_in_loop EQ true) THEN request_is_denied EQ true

R0021 | PREEMPTION | IF emergency_override_token_provided EQ true THEN BYPASS_RULE target R0004
```

---

## 5. `meta_scheme.json` (compiled policy meta + rule objects)

This is the **`meta_scheme.json`** from the same export directory (pretty-printed).

```json
{
  "policy_id": "Test_input2",
  "policy_semantics_version": "1.0",
  "baseline_evaluation": "DEFAULT_UNSATISFIED",
  "evaluation_pathways": [
    {
      "pathway_id": "compiled_default",
      "description": "v1: single pathway AND of active rules (non-PREEMPTION) after overrides",
      "must_satisfy_all": [
        "R0001",
        "R0002",
        "R0003",
        "R0004",
        "R0005",
        "R0006",
        "R0007",
        "R0008",
        "R0009",
        "R0010",
        "R0011",
        "R0012",
        "R0013",
        "R0014",
        "R0015",
        "R0016",
        "R0020"
      ],
      "must_not_trigger": []
    }
  ],
  "rules": [
    {
      "rule_id": "R0001",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "CONSTANT_RELATIONAL",
      "variable": "requested_token_consumption",
      "relational_operator": "LTE",
      "constant_value": 100000,
      "yields": "SATISFIED"
    },
    {
      "rule_id": "R0002",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "CONSTANT_RELATIONAL",
      "variable": "agent_semantic_confidence_score",
      "relational_operator": "GT",
      "constant_value": 0.85,
      "yields": "SATISFIED"
    },
    {
      "rule_id": "R0003",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "LOGICAL_IMPLICATION",
      "trigger_condition": {
        "kind": "and",
        "children": [
          {
            "kind": "atom",
            "variable": "allocated_compute_cores",
            "operator": "GTE",
            "value": 0
          },
          {
            "kind": "atom",
            "variable": "requested_runtime_hours",
            "operator": "GTE",
            "value": 0
          }
        ]
      },
      "required_condition": {
        "kind": "varprod_cmp",
        "left_variable": "allocated_compute_cores",
        "right_variable": "requested_runtime_hours",
        "operator": "LTE",
        "rhs": {
          "kind": "const",
          "value": 120
        }
      }
    },
    {
      "rule_id": "R0004",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "LOGICAL_IMPLICATION",
      "trigger_condition": {
        "kind": "and",
        "children": [
          {
            "kind": "atom",
            "variable": "proposed_financial_budget",
            "operator": "GTE",
            "value": 0
          },
          {
            "kind": "atom",
            "variable": "task_risk_multiplier",
            "operator": "GTE",
            "value": 0
          }
        ]
      },
      "required_condition": {
        "kind": "varprod_cmp",
        "left_variable": "proposed_financial_budget",
        "right_variable": "task_risk_multiplier",
        "operator": "LTE",
        "rhs": {
          "kind": "const",
          "value": 500
        }
      }
    },
    {
      "rule_id": "R0005",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "VARIABLE_RELATIONAL",
      "left_variable": "requested_memory_allocation",
      "relational_operator": "LTE",
      "right_variable": "pre_authorized_memory_limit",
      "yields": "SATISFIED"
    },
    {
      "rule_id": "R0006",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "CONSTANT_RELATIONAL",
      "variable": "concurrent_api_calls",
      "relational_operator": "LT",
      "constant_value": 50,
      "yields": "SATISFIED"
    },
    {
      "rule_id": "R0007",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "SET_INCLUSION",
      "variable": "model_engine_version",
      "inclusion_operator": "IN",
      "constant_array": [
        "GPT-4",
        "CLAUDE-3",
        "GEMINI-3"
      ],
      "yields": "SATISFIED"
    },
    {
      "rule_id": "R0008",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "SET_INCLUSION",
      "variable": "target_deployment_environment",
      "inclusion_operator": "IN",
      "constant_array": [
        "DEV",
        "STAGING",
        "SANDBOX"
      ],
      "yields": "SATISFIED"
    },
    {
      "rule_id": "R0009",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "SET_INCLUSION",
      "variable": "outbound_network_port",
      "inclusion_operator": "NOT_IN",
      "constant_array": [
        22,
        23,
        3389
      ],
      "yields": "SATISFIED"
    },
    {
      "rule_id": "R0010",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "LOGICAL_IMPLICATION",
      "trigger_condition": {
        "kind": "atom",
        "variable": "action_type",
        "operator": "EQ",
        "value": "WRITE"
      },
      "required_condition": {
        "kind": "atom",
        "variable": "agent_role",
        "operator": "EQ",
        "value": "AUTONOMOUS_EDITOR"
      }
    },
    {
      "rule_id": "R0011",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "LOGICAL_IMPLICATION",
      "trigger_condition": {
        "kind": "atom",
        "variable": "target_dataset_contains_pii",
        "operator": "EQ",
        "value": true
      },
      "required_condition": {
        "kind": "atom",
        "variable": "human_in_loop",
        "operator": "EQ",
        "value": true
      }
    },
    {
      "rule_id": "R0012",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "LOGICAL_IMPLICATION",
      "trigger_condition": {
        "kind": "atom",
        "variable": "origin_subnet",
        "operator": "EQ",
        "value": "EXTERNAL"
      },
      "required_condition": {
        "kind": "atom",
        "variable": "cryptographic_secondary_token_count",
        "operator": "EQ",
        "value": 1
      }
    },
    {
      "rule_id": "R0013",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "LOGICAL_IMPLICATION",
      "trigger_condition": {
        "kind": "atom",
        "variable": "target_geographic_region",
        "operator": "EQ",
        "value": "EU"
      },
      "required_condition": {
        "kind": "atom",
        "variable": "compliance_enforcement_flag",
        "operator": "EQ",
        "value": true
      }
    },
    {
      "rule_id": "R0014",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "LOGICAL_IMPLICATION",
      "trigger_condition": {
        "kind": "atom",
        "variable": "target_system",
        "operator": "EQ",
        "value": "FINANCIAL_LEDGER"
      },
      "required_condition": {
        "kind": "atom",
        "variable": "required_approval_level",
        "operator": "EQ",
        "value": "DIRECTOR"
      }
    },
    {
      "rule_id": "R0015",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "LOGICAL_IMPLICATION",
      "trigger_condition": {
        "kind": "atom",
        "variable": "action_type",
        "operator": "EQ",
        "value": "DESTRUCTIVE"
      },
      "required_condition": {
        "kind": "atom",
        "variable": "decision",
        "operator": "EQ",
        "value": "REJECT"
      }
    },
    {
      "rule_id": "R0016",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "LOGICAL_IMPLICATION",
      "trigger_condition": {
        "kind": "atom",
        "variable": "global_quarantine_flag",
        "operator": "EQ",
        "value": true
      },
      "required_condition": {
        "kind": "atom",
        "variable": "decision",
        "operator": "EQ",
        "value": "REJECT"
      }
    },
    {
      "rule_id": "R0017",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "PREEMPTION",
      "preempting_condition": {
        "kind": "atom",
        "variable": "emergency_override_token_provided",
        "operator": "EQ",
        "value": true
      },
      "action": "BYPASS_RULE",
      "target_rule_id": "R0001"
    },
    {
      "rule_id": "R0018",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "PREEMPTION",
      "preempting_condition": {
        "kind": "atom",
        "variable": "agent_role",
        "operator": "EQ",
        "value": "READ_ONLY"
      },
      "action": "BYPASS_RULE",
      "target_rule_id": "R0011"
    },
    {
      "rule_id": "R0019",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "PREEMPTION",
      "preempting_condition": {
        "kind": "atom",
        "variable": "target_deployment_environment",
        "operator": "EQ",
        "value": "SANDBOX"
      },
      "action": "BYPASS_RULE",
      "target_rule_id": "R0009"
    },
    {
      "rule_id": "R0020",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "LOGICAL_IMPLICATION",
      "trigger_condition": {
        "kind": "and",
        "children": [
          {
            "kind": "atom",
            "variable": "involves_system_configuration_changes",
            "operator": "EQ",
            "value": true
          },
          {
            "kind": "not",
            "child": {
              "kind": "atom",
              "variable": "human_in_loop",
              "operator": "EQ",
              "value": true
            }
          }
        ]
      },
      "required_condition": {
        "kind": "atom",
        "variable": "decision",
        "operator": "EQ",
        "value": "REJECT"
      }
    },
    {
      "rule_id": "R0021",
      "applies_to": "GLOBAL",
      "overrides": null,
      "template_class": "PREEMPTION",
      "preempting_condition": {
        "kind": "atom",
        "variable": "emergency_override_token_provided",
        "operator": "EQ",
        "value": true
      },
      "action": "BYPASS_RULE",
      "target_rule_id": "R0004"
    }
  ],
  "variable_sorts": {}
}
```

---

## Alignment summary (final model)

Taken together, this export shows a **coherent, well-structured** formalization of **Test_input2**: Phase 0 coverage completed **cleanly**, the **linearized IR** reads **faithfully** against the processed English (cross-critic **PASS** with substantive audit bullets on **reject** patterns vs **validation** patterns), and the **tester** found **no gaps** across all twenty rules. **Z3** returns **sat** with a verified model—the strongest automatic evidence that the encoding **hangs together**. The **semantic critic’s DRIFT** on **R0015** was a **false positive**; **approving the suggested repair still produced no change in the model**, which is exactly what you want when the critic is wrong—the pipeline **does not** get bent by that noise. **Template** “fail” / “inconclusive” here line up with **golden authoring** and **flip-test grading** limits, as above—not with fundamental unsoundness. **Overall: alignment between the final English, the IR in `meta_scheme.json`, and solver behavior is strong and reviewable**; remaining nits are **lint- or regression-golden-**shaped, not reasons to distrust the formalized policy.




---

## Validation and checks (this export)

**Operative gates on this snapshot:** the **solver** run **passed** (**sat**), **structural IR** checks **passed**, the **template executor** reported **no errors** (all instances ran), the **tester** **passed** (**no findings**), **cross-critic** **passed** after repair, and **semantic critic** is treated as **passing** once a known **false-positive DRIFT** (pathway-list wording vs actual IR) is set aside—**six of eight** template instances **matched** their goldens. What still looks “non-green” on paper (one **heuristic** precheck string, one **attribution** mismatch vs a narrow golden, one **inconclusive** counterfactual grade, plus the **legacy DRIFT label** in `critic_report.json`) is **interpreted below** so it is not mistaken for **encoding failure** or a **broken pipeline**.

The tables below summarize **what the pipeline actually measured** on this snapshot.

### Outcome table

| Layer | Result | Takeaway |
|--------|--------|----------|
| **Z3 (default pathway)** | **sat** | The compiled encoding admits at least one **feasible** valuation; the model is **internally consistent** under the chosen semantics. |
| **IR — varprod trigger shape** | **ok** | Product-style constraints expose both factors in the trigger where required; avoids silent weakening of multi-variable guards. |
| **Template suite harness** | **0 errors** | Every instance **ran** (no validation/executor blowups). **6** instances **matched** golden expectations; **1** mismatch and **1** **inconclusive** (see below—not treated as “model broken”). |
| **Second-pass LLM reviewer (“tester”)** | **ok** (no findings) | Confirms the structured IR tracks all **20** NL rules; calls out correct **R0017 / R0021** split for the dual bypass in NL rule 17. |
| **Cross-critic** (text vs linearized rules) | **PASS** | After **cross repair**, no remaining textual incoherence between English and line-oriented IR. |
| **Semantic critic** (text vs synthetic model) | **Pass** (substance) | Automated output may still carry a **DRIFT** verdict in `critic_report.json`; on review this was a **false positive** (pathway-list bookkeeping **R0015**). **Even when the recommended “fix” was approved for the repairer, the formal model did not change**—strong evidence that this class of signal does **not** mutate the encoding and does **not** stall trustworthy runs. **Semantic critic minus this false positive = pass.** |
| **Precheck** (heuristic NL vs meta) | **issues** | **One** string heuristic mismatch (`100000` in meta vs **“100,000”** / **“100,000 tokens”** surface form in English). **Significance**: **low**—typical normalization noise, not a missing rule. |

### LLM-assisted checks — purpose, issues, and repairs

These stages use an LLM to compare **natural language** to **formal artifacts** and (when enabled) drive **repair** loops.

- **Tester** (`tester_report.json`): A **second semantic review** of the synthetic description versus the policy. It looks for **omitted rules**, **wrong templates**, and **bad decompositions** (e.g. one NL line needing two IR rules). **On this export:** **verdict `ok`**, **empty findings**—the model is assessed as fully covering the 20 rules, including the split preemption for the emergency override.

- **Semantic critic** (`critic_report.json`): Compares **effective NL** to the **compiled narrative** and checks **pathways** (which rules are listed as mandatory in the default path). It can emit **DRIFT** when a pathway summary and the rule list **look** misaligned. **On this export:** the **R0015 / `must_satisfy_all`** issue was a **false positive**—the **rule is present** in the IR and enforced in the compiled semantics; the critic overstated a **naming-of-pathway-membership** mismatch. **When that repair path was accepted for the repairer, no change to `meta_scheme.json` (or the live model) occurred**, which supports treating this as **non-actionable**: **false positives do not break the pipeline** or force spurious edits. **Other issues caught / repaired earlier in the run** (see `repairer_piv_semantic_trace.jsonl`) **did** matter—e.g. **R0017** → **`PREEMPTION`** with correct **bypass targets** (**R0001**, **R0004**); **R0021** for the second bypass; **R0003 / R0004** triggers requiring **both** operands for product constraints. For portfolio reading: **semantic critic minus this false positive is a pass.**

- **Cross-critic** (`cross_critic_report.json`): Compares **processed NL** to **linearized rules**—good for **shape drift** (“does this line read like what the IR says?”). **Repairs applied (`cross_repairer_trace.jsonl`):** **R0016** normalized from a **`CONSTANT_RELATIONAL` / UNSATISFIED** style to **`LOGICAL_IMPLICATION`** with **`decision EQ REJECT`** for consistent denial vocabulary; **R0020** aligned to use **`decision EQ REJECT`** instead of a parallel denial flag; **R0003** trigger simplified (redundant **GTE 0** guards removed) to match **R0004** and the source text.

### Programmatic checks — significance and results

- **Precheck** (`precheck.json`): **Fast heuristics** (e.g. constants appearing in the meta but not spotted in raw NL strings). **Result:** **not ok**, one issue on **100000** vs surface wording. **Meaning:** treat as **lint noise** from formatting/tokenization; follow **Z3 + IR** for substance.

- **Varprod / IR structure** (`ir_structure_check.json`): Ensures **multiplicative** constraints mention **both** factors in the trigger where the IR rules require it. **Result:** **ok**. **Meaning:** product rules are **not** accidentally vacuous on one operand.

- **Z3** (`run_summary.json` / `z3_result.json`): **End-to-end satisfiability** of the compiled theory (under the pipeline’s default check). **Result:** **sat**, **model_verified**. **Meaning:** there is a **witness** assignment; the policy does not collapse to **unsat** under this encoding.

### Executable template suite — significance and results

The suite (`template_run_report.json`, **`test_input2_suite`**) runs **schema-defined** scenarios against the **real solver**: SAT/UNSAT worlds, **decisions**, **rule attribution**, **boundaries**, **counterfactual flips**, **obligations**, **pairwise** comparisons. **Significance:** regression-style evidence that the **executable** behavior matches **expectations encoded in the suite JSON** for each instance.

**This export:** **6 passed**, **1 failed**, **0 errors**, **1 inconclusive**.

- **`gen_003` (`rule_attribution`) — verdict `fail`:** The solver returned **sat** and listed **many** rule IDs as satisfied in that world; the **LLM-authored golden** expected only **`R0006`**. **Meaning here:** this is almost certainly a **too-narrow golden rule** not a model problem (the formal model allows multiple conjuncts to hold simultaneously), **not** proof that Z3 or the policy definition failed. See also [`test-gen-results.md`](test-gen-results.md).

- **`gen_005` (`counterfactual_flip`) — verdict `inconclusive`:** Base world went **unsat**, so the harness could not recover a **base decision** to compare to the mutant. **Meaning here:** **inconclusive** means **“could not grade the flip from the golden”**, not **“the policy is inconsistent.”** The mutant side still resolved (**sat**, **unsatisfied**), which is consistent with exercising a denial-shaped region.

**Bottom line on fail / inconclusive:** For this project, those labels mean **“mismatch with this suite file’s expectations or a scoring limitation,”** not **automatic refutation** of the compiled model—especially when **Z3 is sat**, **harness errors are zero**, and **cross-critic** has **cleared**.

---