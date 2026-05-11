# Synthetic policy (Test_input)
Semantics: 1.0

## Rules
- **R0001** (SET_INCLUSION) applies_to=GLOBAL overrides=None
- **R0002** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0003** (CONSTANT_RELATIONAL) applies_to=GLOBAL overrides=None
- **R0004** (CONSTANT_RELATIONAL) applies_to=GLOBAL overrides=None
- **R0005** (VARIABLE_RELATIONAL) applies_to=GLOBAL overrides=None
- **R0006** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None
- **R0007** (PREEMPTION) applies_to=GLOBAL overrides=None
- **R0008** (LOGICAL_IMPLICATION) applies_to=GLOBAL overrides=None

## Pathway note (v1)
Evaluation pathways list **`must_satisfy_all`** entries for **non-PREEMPTION** rules only. **PREEMPTION** rules still appear under **Rules** above and are applied in the policy checker (Z3); their omission from `must_satisfy_all` is by design, not a missing obligation.

### PREEMPTION detail
- **R0007**: action=BYPASS_RULE, target_rule_id=R0003

## Pathways
### compiled_default
- description: v1: single pathway AND of active rules (non-PREEMPTION) after overrides
- must_satisfy_all: ['R0001', 'R0002', 'R0003', 'R0004', 'R0005', 'R0006', 'R0008']
- must_not_trigger: []
