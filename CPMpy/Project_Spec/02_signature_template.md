# Signature Template

A signature defines the typed vocabulary the formalizer is constrained to use for a given domain. One signature file per domain.

This document specifies the **abstract structure** of a signature. It contains no domain-specific symbols. For a concrete instantiation showing what an actual signature looks like with real values, see the example domain artifact.

The distinction matters: a signature is a schema. A populated signature for a specific domain is an instance of that schema. Cursor must implement the schema, not hardcode any of the example values from the example domain into the schema.

The signature scope covers the full CPMpy expressivity surface: scalar variables, vector variables (`shape=`), global constraints, nested helpers, and optimization-style constraints. **CONFLICT** callouts mark places where this scope affects validation or runtime behavior.

---

## What a signature must contain

Every signature file must define seven sections in this order. Names in `<angle_brackets>` are placeholders to be filled in per domain.

### Section 1 — Imports

```python
import cpmpy as cp
# Optional additional imports declared by the domain operator
```

The pipeline allowlist starts with `cpmpy as cp`. Additional imports are declared here and the AST validator extends its allowlist accordingly.

### Section 2 — Enumerations

Each enum is a Python dict mapping symbolic names to integer codes.

```python
<ENUM_NAME> = {"<VALUE_NAME_1>": 0, "<VALUE_NAME_2>": 1, ...}
```

Required properties:
- Variable name in UPPER_SNAKE_CASE.
- Values are strings; codes are sequential integers starting at 0.
- At least two values per enum.

A signature may have zero enums if all fields are numeric or boolean.

### Section 3 — Entity field declarations (scalar)

Each scalar entity field is a CPMpy decision variable: `intvar` for integers, `boolvar` for booleans.

```python
<entity>_<field_name> = cp.intvar(<lower>, <upper>, name="<entity>_<field_name>")
<entity>_<bool_field_name> = cp.boolvar(name="<entity>_<bool_field_name>")
```

Required properties:
- Variable name in lower_snake_case with entity prefix.
- The `name=` argument matches the variable name exactly. AST validator checks this.
- Numeric bounds are explicit integers, never `None`.
- A field is not redefined under multiple names.

### Section 4 — Entity field declarations (vector)

Vector fields are CPMpy variables declared with `shape=`. Used for collections of entities or grids of values.

```python
<collection_name> = cp.intvar(<lower>, <upper>, shape=<shape>, name="<collection_name>")
<collection_bool_name> = cp.boolvar(shape=<shape>, name="<collection_bool_name>")
```

Required properties:
- Variable name describes the collection (`tasks`, `nurses_shifts`, `slots_assigned`), not a single element.
- Shape is one of:
  - A positive integer (1D vector).
  - A tuple of positive integers (multi-dimensional grid).
  - A symbolic dimension name declared in section 7's `DOMAIN_DIMENSIONS` (e.g., `(NUM_NURSES, NUM_DAYS)`).
- Bounds are explicit integers.
- The `name=` argument matches the variable name.

> **CONFLICT — vector fields create state-extraction routing.** The runtime extractor needs to know whether a tool needs the full vector, a slice, or a single element. This is declared per-tool in `TOOL_DEPENDENCIES` (section 8 below), not in the field declaration itself.

A signature may have zero vector fields. If section 4 is empty, the pipeline operates entirely on scalars (faster verification, faster runtime).

### Section 5 — Tool-call parameter declarations

Each gated tool's parameters as CPMpy variables, naming convention `<tool>_call_<parameter_name>`.

```python
<tool>_call_<parameter_name> = cp.intvar(<lower>, <upper>, name="<tool>_call_<parameter_name>")
```

Tool parameters can themselves be vectors if a tool takes a collection as input (e.g., a batch operation). Same `shape=` syntax as section 4.

Multiple gated tools have their parameters in separate subsections.

### Section 6 — Derived helpers (optional)

Helpers are CPMpy expressions over fields, enums, and other helpers.

```python
<helper_name> = (<expression involving fields, enums, or earlier helpers>)
```

Required properties:
- Helper name in lower_snake_case.
- The expression is a single CPMpy expression — no Python control flow, no statements.
- Helpers may reference earlier helpers (helpers nest). This is permitted in full-scope.
- Helpers must be acyclic. The AST validator confirms this by topological sort over the helper dependency graph.

> **CONFLICT — nested helpers require dependency-graph validation.** The earlier flat-helpers rule was lifted. The AST validator now builds a directed graph of helper-references-helper, checks for cycles (rejection on cycle), and topologically sorts so each helper's expression is well-defined before any helper that references it.

If no helpers are needed, this section can be empty.

### Section 7 — Domain dimensions (required if section 4 is non-empty)

A Python dict at module top level, named exactly `DOMAIN_DIMENSIONS`. Maps symbolic dimension names to integers.

```python
DOMAIN_DIMENSIONS = {
    "<DIMENSION_NAME_1>": <integer>,
    "<DIMENSION_NAME_2>": <integer>,
}
```

Required properties:
- Names in UPPER_SNAKE_CASE.
- Values are positive integers.
- Every symbolic dimension referenced in section 4 or section 5 is declared here.

Also includes test-time bounds for property-based testing (separate from production dimensions, used to keep Hypothesis state generation tractable):

```python
TEST_SHAPE_BOUNDS = {
    "<DIMENSION_NAME_1>": <integer_for_testing>,
}
```

> **CONFLICT — test-time bounds may differ from production bounds.** A scheduler may have `NUM_TASKS = 1000` in production, but Hypothesis cannot exhaustively explore states over a vector of 1000 ints. The test-time bound shrinks the dimension for testing. The pipeline reads `TEST_SHAPE_BOUNDS` and constructs a parallel signature for testing purposes; the production signature is used at runtime.

If section 4 is empty, `DOMAIN_DIMENSIONS` and `TEST_SHAPE_BOUNDS` may be omitted.

### Section 8 — Tool-to-state-dependency manifest

A Python dict at module top level, named exactly `TOOL_DEPENDENCIES`. Schema:

```python
TOOL_DEPENDENCIES = {
    "<tool_name>": [
        "<scalar_symbol>",
        {"name": "<vector_symbol>", "slice": "full"},
        {"name": "<vector_symbol>", "slice": "by_index", "index_param": "<call_param_name>"},
        {"name": "<vector_symbol>", "slice": "by_range", "lower_param": "<param_a>", "upper_param": "<param_b>"},
    ],
    "<another_tool_name>": [...],
}
```

Required properties:
- Keys are tool names matching `tools.json`.
- Values are lists; each entry is either a string (scalar symbol) or a dict with a `name` and `slice` field.
- Slice modes for vector dependencies:
  - `"full"` — entire vector materialized.
  - `"by_index"` — single element, index drawn from a call parameter.
  - `"by_range"` — slice with bounds drawn from call parameters.
- Every gated tool in `tools.json` appears as a key.
- Every named symbol exists in sections 2–6.

> **CONFLICT — vector dependencies require slice metadata.** A tool that operates on a single element of a vector should declare `by_index`, not `full`, so the runtime extracts only what's needed. The pipeline does not infer slice mode; the domain operator declares it.

A symbol may appear in multiple tools' dependency lists.

---

## What the AST validator enforces against the signature

When a formalizer-produced rule is validated:

- All imports in the rule must be in the signature's section 1 allowlist.
- All names referenced must be declared in sections 2–6 or be Python literals or comprehension-bound variables.
- For a rule scoped to tool T, names referenced must appear in `TOOL_DEPENDENCIES[T]` (section 8), with the exception of helpers from section 6 (which may be referenced from any tool's rules provided their own dependencies are subsumed by `TOOL_DEPENDENCIES[T]`).
- Helper references resolve through the helper dependency graph; cycles are rejected.
- Comprehensions are allowed only over signature-declared collections or literal `range(...)` with constant bounds drawn from `DOMAIN_DIMENSIONS`.
- No statement-level control flow (`if`, `while`, `for`), no function or class definitions, no mutation.
- The `used_symbols`, `uses_global_constraints`, and `uses_vector_variables` lists/flags emitted by the formalizer must match the AST.

---

## What the formalizer LLM is shown

For each rule formalization call:

- The full signature file (all eight sections, populated for the current domain).
- The full glossary file.
- A small set of few-shot examples that have already been verified for this domain, or seed examples for the first rules.
- The single NL rule it is currently formalizing, along with which tool's rules it belongs to.

> **CONFLICT — seed few-shot examples must demonstrate full scope.** The default seed set must include scalar examples, vector examples (with comprehensions and slicing), and at least one global-constraint example (`AllDifferent` is a good default). Without these the formalizer will systematically under-use full CPMpy expressivity. Cursor produces this seed set as part of the prompts artifact.

The formalizer emits a CPMpy boolean expression assigned to a name, plus the metadata flags described in the project specification's section 3.

---

## What changes per domain vs. what stays constant

Per-domain (filled in by the domain operator):
- The specific enums, fields, parameters, helpers, dimensions, and tool dependencies.
- Numeric bounds.
- Whether vector fields and/or global constraints are used at all.

Constant across domains:
- The eight-section structure.
- Naming conventions.
- The CPMpy-API allowlist.
- The `DOMAIN_DIMENSIONS`, `TEST_SHAPE_BOUNDS`, and `TOOL_DEPENDENCIES` schemas.
- The AST validator's enforcement rules.

If Cursor finds itself writing logic that depends on specific enum values or specific field names, that logic belongs in a domain instantiation, not in the pipeline.

---

## Where to look for a worked example

The example domain artifact (`03_example_domain.md`) shows a populated signature for a refund-policy domain (scalar-only, no vectors, no globals — a deliberately minimal case to demonstrate the structure). For a signature exercising the full scope (vectors, globals, nested helpers), a second domain instantiation should be authored as part of the v1 success criteria.
