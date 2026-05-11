# Synthetic policy (Test_input)
Semantics: 1.0

## Rules
- **R0001** (CONSTANT_RELATIONAL) applies_to=GLOBAL overrides=None
- **R0002** (CONSTANT_RELATIONAL) applies_to=GLOBAL overrides=None
- **R0003** (VARIABLE_RELATIONAL) applies_to=GLOBAL overrides=None
- **R0004** (CONSTANT_RELATIONAL) applies_to=GLOBAL overrides=None

## Pathways
### compiled_default
- description: v1: single pathway AND of active rules (non-PREEMPTION) after overrides
- must_satisfy_all: ['R0001', 'R0002', 'R0003', 'R0004']
- must_not_trigger: []
