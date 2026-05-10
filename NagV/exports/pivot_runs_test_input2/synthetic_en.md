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
