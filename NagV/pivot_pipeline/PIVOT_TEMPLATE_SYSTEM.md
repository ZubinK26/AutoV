# Pivot template system — introduction and rules (v1)

This document is a single introduction to how the **pivot policy pipeline** represents natural-language rules in a **closed, machine-checkable IR**, compiles them into a **meta-scheme**, and grounds them for **Z3**. It complements the formal contract in [`../Extract-Pivot.md`](../Extract-Pivot.md), the extractor prompt [`prompts/extractor.md`](prompts/extractor.md), and the normative limits in [`prompts/v1_policy_encodability_contract.md`](prompts/v1_policy_encodability_contract.md).

---

## 1. Core ideas

### 1.1 One English line → one JSON rule

Phase 1 extraction turns **one** normalized policy line into **one** JSON object. That object has **exactly one** `template_class` chosen from a **fixed list of eight**. You **cannot** merge two templates in one object (e.g. no “both `CONSTANT_RELATIONAL` and `LOGICAL_IMPLICATION`” on the same rule). Rich combinations appear inside **`LOGICAL_IMPLICATION`** / **`LOGICAL_IFF`** / **`PREEMPTION`** via nested **`ConditionExpr`** trees, or by using **several** rules with routing keys.

### 1.2 What the pipeline does with rules

1. **Extract** + **registry** → `rules_extracted.json` (list of rule objects).
2. **Pathway compiler** → `meta_scheme.json`: attaches **evaluation pathways** (which non-preemption rules must hold together) and keeps **PREEMPTION** rules in `rules[]` for the encoder (pathway lists intentionally omit pure preemption rows by v1 design).
3. **Z3 compilation** → satisfiability and scenario checks.

### 1.3 Validation

Structured LLM output is **parsed as JSON** and validated against **Pydantic** models (same contract as this document). Invalid shape → retries or a **hard stop** on that step—not silent acceptance.

---

## 2. The eight `template_class` values (closed vocabulary)

Spell **exactly** as below (uppercase, underscores). **No other strings** are valid. If a line cannot be encoded without inventing a new type, extract must respond:

`ABORT: Ruleset exceeds decidable scope.`

| `template_class` | Plain meaning |
|------------------|----------------|
| **`CONSTANT_RELATIONAL`** | One variable compared to a **constant** (`EQ`, `NEQ`, `GT`, `LT`, `GTE`, `LTE`), with a **yields** outcome (`SATISFIED` / `UNSATISFIED`). |
| **`SET_INCLUSION`** | One variable must be **IN** or **NOT_IN** a **finite literal list**; **yields**. |
| **`VARIABLE_RELATIONAL`** | **Two** variables compared (`left_variable`, `right_variable`, operator, **yields**). |
| **`ARITHMETIC_EVALUATION`** | **One** linear arithmetic step (`ADD` / `SUBTRACT` / `MULTIPLY` / `DIVIDE`) then compare to a **target_limit**; **yields**. **Multiply** is restricted: **no variable × variable** for `MULTIPLY` (`operand_2` must not be another variable name). **Divide**: divisor must be numeric. |
| **`LOGICAL_IMPLICATION`** | **If** `trigger_condition` **then** `required_condition`. Both sides are **`ConditionExpr`** (nested AND / OR / NOT, atoms, etc.). |
| **`PREEMPTION`** | When `preempting_condition` holds, apply **`FORCE_SATISFIED`**, **`FORCE_UNSATISFIED`**, or **`BYPASS_RULE`** to an **earlier** rule via **`target_rule_id`** (must **not** reference another `PREEMPTION`). |
| **`EXCLUSIVE_CHOICE`** | Among **≥ two** variables: **`exactly_one`** or **`at_most_one`** must hold. |
| **`LOGICAL_IFF`** | **If and only if** between `left` and `right` **`ConditionExpr`**. |

Domain phrases (“access rule”, “decision template”, …) **must never** appear as `template_class`; they map into this list.

---

## 3. Every rule carries routing keys

In addition to `template_class` and fields for that template:

| Field | Role |
|--------|------|
| **`rule_id`** | Stable id (`R0001`, …), may be assigned/overwritten by the pipeline. |
| **`applies_to`** | **`"GLOBAL"`** or another rule’s **`rule_id`**. **GLOBAL** = default pathway attachment. Non-global = dependency / scoping for pathway construction. |
| **`overrides`** | **`null`** or a **`rule_id`** this rule **supersedes** when pathways are cloned (exception / replacement wiring in the meta-scheme graph). |

**Routing is not “if-then logic” inside Z3**—it tells the **compiler** how rules are grouped into **pathways**. **Conditional policy** is mostly **`LOGICAL_IMPLICATION`** and **`PREEMPTION`**.

---

## 4. Nesting: `ConditionExpr`

Nested boolean structure and guarded comparisons use **`ConditionExpr`** (see [`prompts/extractor.md`](prompts/extractor.md)).

- **Where it appears:** `LOGICAL_IMPLICATION` (`trigger_condition`, `required_condition`), `LOGICAL_IFF` (`left`, `right`), `PREEMPTION` (`preempting_condition`).
- **Kinds:** `atom`, `varcmp`, `varprod_cmp`, `and`, `or`, `not`.
- **`and` / `or`:** **at least two** children.
- **Max depth:** `CONDITION_EXPR_MAX_DEPTH` in code (**8** in v1).
- **`varprod_cmp` (variable × variable product):** at most **one** `varprod_cmp` **across all condition trees of that single rule** (trigger + required combined). **Factors** must not be variables listed in **`EXCLUSIVE_CHOICE`**. Integers used in products are bounded for Z3 (see contract / `PIVOT_PRODUCT_INT_CAP`).

**Flat templates** (`CONSTANT_RELATIONAL`, `SET_INCLUSION`, `VARIABLE_RELATIONAL`, `ARITHMETIC_EVALUATION`, `EXCLUSIVE_CHOICE`) do **not** use a `ConditionExpr` tree in the same way—they are single structured assertions.

---

## 5. Expressivity: what is in scope

**In scope (typical):**

- Boolean combinations of comparisons, bounded linear arithmetic, finite enumerations, **if-then** and **iff** policies, **mutually exclusive** flags, **preemptions / bypasses** targeting earlier rules.
- Compilation target: **SMT**-friendly theories (guarded linear / QF-LIA style usage as in project docs), **satisfiability** checks, scenario tests.

**Out of scope / causes ABORT or rewrite:**

- New **`template_class`** names.
- **Multiple distinct products** in one rule beyond the **single** allowed `varprod_cmp` pattern per rule, or products on **choice** variables where forbidden.
- **`ARITHMETIC_EVALUATION`** with **variable × variable** multiply.
- **Non-linear** or unconstrained arithmetic that breaks the encodability contract.
- **Imperative programs**, arbitrary **time / loops**, unconstrained **quantifiers** over infinite domains—policy lines must map to the **flat + ConditionExpr** shapes above.

The pipeline is built for **stateless policy-style constraints**, not general mathematics or Turing-complete control flow.

---

## 6. Meta-scheme (summary)

`meta_scheme.json` holds:

- **`policy_id`**, **`policy_semantics_version`**, **`baseline_evaluation`** (e.g. default unsatisfied until a pathway holds).
- **`evaluation_pathways[]`**: each pathway lists **`must_satisfy_all`** (non-preemption rules that must conjunctively hold on that path) and **`must_not_trigger`**.
- **`rules[]`**: **all** rules, including **PREEMPTION** (preemptions apply in Z3 even when **omitted** from `must_satisfy_all` lists by v1 design).

---

## 7. Reference snapshot (archived export)

The following three blocks are copied from the **versioned** workspace **`NagV/exports/pivot_runs_test_input2/`**: **processed NL** used as the line-per-rule input stream after Phase 0 (**`rules_source.txt`**), **synthetic English** produced by deterministic back-translation from the meta-scheme (**`synthetic_en.md`**), and the full **`meta_scheme.json`** for policy **`Test_input2`** (`policy_semantics_version` **1.0**). They are **documentation examples**; your own runs will produce paths under `--work-dir`.

### 7.1 Processed NL (`rules_source.txt`)

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

### 7.2 Synthetic English (`synthetic_en.md`)

```markdown
# Synthetic policy (Test_input2)
Semantics: 1.0

## Rules
- **R0001** (CONSTANT_RELATIONAL) applies_to=GLOBAL overrides=None
- **R0002** (CONSTANT_RELATIONAL) applies_to=GLOBAL overrides=None
- **R0003** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0004** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0005** (VARIABLE_RELATIONAL) applies_to=GLOBAL overrides=None
- **R0006** (CONSTANT_RELATIONAL) applies_to=GLOBAL overrides=None
- **R0007** (SET_INCLUSION) applies_to=GLOBAL overrides=None
- **R0008** (SET_INCLUSION) applies_to=GLOBAL overrides=None
- **R0009** (SET_INCLUSION) applies_to=GLOBAL overrides=None
- **R0010** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0011** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0012** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0013** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0014** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0015** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0016** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0017** (PREEMPTION) applies_to=GLOBAL overrides=None
- **R0018** (PREEMPTION) applies_to=GLOBAL overrides=None
- **R0019** (PREEMPTION) applies_to=GLOBAL overrides=None
- **R0020** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0021** (PREEMPTION) applies_to=GLOBAL overrides=None

## Pathway note (v1)
Evaluation pathways list **`must_satisfy_all`** entries for **non-PREEMPTION** rules only. **PREEMPTION** rules still appear under **Rules** above and are applied in the policy checker (Z3); their omission from `must_satisfy_all` is by design, not a missing obligation.

### PREEMPTION detail
- **R0017**: action=BYPASS_RULE, target_rule_id=R0001
- **R0018**: action=BYPASS_RULE, target_rule_id=R0011
- **R0019**: action=BYPASS_RULE, target_rule_id=R0009
- **R0021**: action=BYPASS_RULE, target_rule_id=R0004

## Pathways
### compiled_default
- description: v1: single pathway AND of active rules (non-PREEMPTION) after overrides
- must_satisfy_all: ['R0001', 'R0002', 'R0003', 'R0004', 'R0005', 'R0006', 'R0007', 'R0008', 'R0009', 'R0010', 'R0011', 'R0012', 'R0013', 'R0014', 'R0015', 'R0016', 'R0020']
- must_not_trigger: []
```

### 7.3 Full `meta_scheme.json` (`Test_input2`, v1.0)

The following JSON matches `NagV/exports/pivot_runs_test_input2/meta_scheme.json` at the time this document was generated.

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

See also [`ARCHITECTURE.md`](ARCHITECTURE.md) for the end-to-end pipeline and [`../../example_run_artifact_bundle.md`](../../example_run_artifact_bundle.md) for a single-file walkthrough of this export.
