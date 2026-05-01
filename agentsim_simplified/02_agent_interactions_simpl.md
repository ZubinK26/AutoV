# Agent Interactions Specification (simplified)

Spec tree: `01_simulation_environment_simpl.md`, `02_agent_interactions_simpl.md`, `03_validation_workflow_simpl.md`, `04_agentic_guardrails_simpl.md`.

## Purpose

Define how the "agent" interacts with the simulation tonight. To keep the scope tight, the agent is **not** an LLM in v1. It is a scripted Python sequence of tool-call objects that exercises the runtime end-to-end. This is enough to prove the architecture works. LLM integration is a v2 add and is explicitly deferred.

## Why scripted instead of LLM tonight

The point of the project is to prove that the runtime gates correctly. A scripted sequence proves that with zero LLM-flakiness, zero API debugging at midnight, and zero risk that the demo fails because of model drift. Once the runtime is proven, dropping in a real LLM is a small change later: replace the script with a chat loop that asks the LLM to produce one of the same tool-call objects.

## Tool-call object shape

Every proposed tool call is a Python dataclass:

```python
@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    parameters: dict[str, Any]
```

Two tools are valid: `"lookup_bundle"` and `"apply_refund"`. Schemas:

- `lookup_bundle`: parameters `{"transaction_id": str}`
- `apply_refund`: parameters `{"transaction_id": str, "amount_pence": int, "refund_type": str, "reason": str}`

Malformed calls (wrong keys, wrong types) raise a `SchemaError` before the validator is invoked. This is distinct from a policy violation.

## Scenario

A scenario is a hardcoded list of tool calls plus an English description of what each call is meant to demonstrate. The runner walks the list, executes each, appends the result to the trace, and stops at the end. There is no branching, no agent decision-making, no looping based on tool results — just a linear playback.

The single scenario for tonight is `scenario_demo`. It must hit:
- one clean ALLOW
- one BLOCK on FAILED KYC
- one BLOCK on the sanctions block flag
- one BLOCK on the goodwill rolling-window cap
- one BLOCK on the refund-amount-exceeds-original rule

## scenario_demo (concrete)

Each entry below is a (description, ToolCall) tuple. Cursor should encode this directly.

1. ("Look up a clean transaction for C-001", ToolCall("lookup_bundle", {"transaction_id": "T-001"})) — expected result: returns a StateBundle, no decision needed.

2. ("Issue a £30 merchant refund on T-001 — should ALLOW", ToolCall("apply_refund", {"transaction_id": "T-001", "amount_pence": 3000, "refund_type": "MERCHANT_REFUND", "reason": "merchant agreed to refund partial amount"})) — expected: ALLOW, refund created.

3. ("Look up T-004 (customer has FAILED KYC)", ToolCall("lookup_bundle", {"transaction_id": "T-004"})) — expected: returns a StateBundle.

4. ("Try a refund on T-004 — should BLOCK on KYC", ToolCall("apply_refund", {"transaction_id": "T-004", "amount_pence": 2000, "refund_type": "MERCHANT_REFUND", "reason": "support request"})) — expected: BLOCK, unsat core references the FAILED-KYC rule.

5. ("Look up T-005 (account has sanctions block)", ToolCall("lookup_bundle", {"transaction_id": "T-005"})) — expected: returns a StateBundle.

6. ("Try a refund on T-005 — should BLOCK on sanctions", ToolCall("apply_refund", {"transaction_id": "T-005", "amount_pence": 3000, "refund_type": "MERCHANT_REFUND", "reason": "support request"})) — expected: BLOCK, unsat core references the sanctions-block rule.

7. ("Look up T-003 (customer near goodwill cap)", ToolCall("lookup_bundle", {"transaction_id": "T-003"})) — expected: returns a StateBundle.

8. ("Try a £10 goodwill credit for C-003 — should BLOCK (49500 + 1000 = 50500 exceeds cap)", ToolCall("apply_refund", {"transaction_id": "T-003", "amount_pence": 1000, "refund_type": "GOODWILL_CREDIT", "reason": "service issue"})) — expected: BLOCK, unsat core references the goodwill rolling-window rule. (49500 + 1000 = 50500, which exceeds 50000.)

9. ("Look up T-006 (8k transaction)", ToolCall("lookup_bundle", {"transaction_id": "T-006"})) — expected: returns a StateBundle.

10. ("Try a £100 refund on T-006 (transaction was £80) — should BLOCK on amount-exceeds-original", ToolCall("apply_refund", {"transaction_id": "T-006", "amount_pence": 10000, "refund_type": "MERCHANT_REFUND", "reason": "support overrefunded"})) — expected: BLOCK, unsat core references the refund-amount-exceeds-original rule. (Transaction T-006 is 8000 pence; the refund proposes 10000 pence.)

That's ten steps, five gated calls, four BLOCKs and one ALLOW, each BLOCK exercising a distinct rule.

## Runner

A single `run_scenario(scenario)` function:

```
def run_scenario(scenario):
    trace = []
    db = load_db()
    for step, (description, call) in enumerate(scenario, start=1):
        trace_entry = execute_call(call, db, step, description)
        trace.append(trace_entry)
    print_trace(trace)
    print_summary(trace)
```

`execute_call` dispatches to the tool function, captures the decision and result, builds a TraceEntry. `print_trace` is a pretty-printer; `print_summary` counts ALLOW vs BLOCK and lists which rules fired.

## What the runner does NOT do tonight

- Does not call any LLM.
- Does not mutate the trace's order or skip steps based on prior outcomes.
- Does not retry blocked calls.
- Does not produce a JSON output file (stdout only is fine; piping to a file is the user's choice).

## V2 LLM hook (do not implement tonight, but write the seam)

The scripted scenario should live in a separate module from the runner, and the runner's `for` loop should accept *any* iterable of `(description, ToolCall)`. That means tomorrow's LLM integration is a generator that yields tool calls based on a running conversation, plugged into the same runner. Don't build it tonight; just don't make architectural choices that prevent it.

## Deliverables for Cursor

- `agent.py` — defines `ToolCall`, `SchemaError`, and `scenario_demo` as a list
- `runner.py` — `run_scenario`, `execute_call`, `print_trace`, `print_summary`, plus a `if __name__ == "__main__": run_scenario(scenario_demo)` block
