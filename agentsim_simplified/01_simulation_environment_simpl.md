# Simulation Environment Specification (simplified)

Spec tree: `01_simulation_environment_simpl.md`, `02_agent_interactions_simpl.md`, `03_validation_workflow_simpl.md`, `04_agentic_guardrails_simpl.md`. See `dev_plans/dev_plan_agentsim_simplified_v1.md`.

## Purpose

A minimal, in-process simulation of a UK retail-bank refund-handling context. The whole thing runs in one Python process, with seed data hardcoded as Python objects. No SQLite, no network, no real LLM unless explicitly added. The goal is to prove the runtime-validation architecture end-to-end on a tightly scoped slice.

## Scope cuts deliberately taken

- One write tool only: apply_refund.
- One read tool: lookup_bundle.
- Two refund types: MERCHANT_REFUND and GOODWILL_CREDIT.
- Four entity types: Customer, Account, Transaction, Refund.
- In-memory dict-based "DB". No persistence between runs.
- No LLM in v1; the agent is a scripted sequence of tool calls. LLM integration is a v2 add.
- One scripted scenario hitting five rule outcomes (one ALLOW, four BLOCKs).

## Entity model

Use Python `@dataclass(frozen=True)` for each. All identifiers are strings; all monetary amounts are integers in pence; no floats anywhere.

### Customer
- `customer_id: str`
- `kyc_status: Literal["VERIFIED", "FAILED"]`
- `vulnerable_flag: bool`
- `recent_goodwill_credit_total_pence: int`

### Account
- `account_id: str`
- `customer_id: str`
- `status: Literal["ACTIVE", "FROZEN", "CLOSED"]`
- `has_sanctions_block: bool`

### Transaction
- `transaction_id: str`
- `account_id: str`
- `amount_pence: int`
- `status: Literal["POSTED", "PENDING"]`

### Refund (output entity, created by the tool)
- `refund_id: str`
- `transaction_id: str`
- `customer_id: str`
- `amount_pence: int`
- `refund_type: Literal["MERCHANT_REFUND", "GOODWILL_CREDIT"]`
- `reason: str`

## In-memory database

A single module-level dict keyed by entity type:

```python
DB = {
    "customers": {customer_id: Customer, ...},
    "accounts": {account_id: Account, ...},
    "transactions": {transaction_id: Transaction, ...},
    "refunds": {},  # populated as the scenario runs
}
```

Seed data is loaded by `seed_data.py` at startup. After each scenario, the runner can reset the DB by reloading the seed.

## Seed data

Five customers, five accounts (one per customer), seven transactions. Designed so the scripted scenario hits all five required outcomes.

Customers:

| customer_id | kyc_status | vulnerable_flag | recent_goodwill_credit_total_pence |
|---|---|---|---|
| C-001 | VERIFIED | false | 0 |
| C-002 | VERIFIED | true | 0 |
| C-003 | VERIFIED | false | 49500 |
| C-004 | FAILED | false | 0 |
| C-005 | VERIFIED | false | 0 |

Accounts:

| account_id | customer_id | status | has_sanctions_block |
|---|---|---|---|
| A-001 | C-001 | ACTIVE | false |
| A-002 | C-002 | ACTIVE | false |
| A-003 | C-003 | ACTIVE | false |
| A-004 | C-004 | ACTIVE | false |
| A-005 | C-005 | ACTIVE | true |

Transactions:

| transaction_id | account_id | amount_pence | status |
|---|---|---|---|
| T-001 | A-001 | 5000 | POSTED |
| T-002 | A-002 | 30000 | POSTED |
| T-003 | A-003 | 2000 | POSTED |
| T-004 | A-004 | 4000 | POSTED |
| T-005 | A-005 | 6000 | POSTED |
| T-006 | A-001 | 8000 | POSTED |
| T-007 | A-001 | 1500 | PENDING |

## Tool surface

### Read: lookup_bundle(transaction_id) -> StateBundle | None
Returns a `StateBundle` containing the transaction, the account it belongs to, and the customer who owns the account. Returns `None` if any of those don't resolve. Never gated.

`StateBundle` is a frozen dataclass with fields `customer: Customer`, `account: Account`, `transaction: Transaction`.

### Write: apply_refund(transaction_id, amount_pence, refund_type, reason) -> Refund | RefundError
The only gated tool. Every call goes through the validator before execution. On ALLOW, creates a Refund and appends to `DB["refunds"]`. On BLOCK, returns a `RefundError` with the rule IDs from the unsat core and a human-readable explanation.

## Tool-call lifecycle

```
proposed_call -> validator(call, state_bundle) -> Decision
                                                |
                                                +--ALLOW--> execute, log entry
                                                |
                                                +--BLOCK--> error, log entry
```

Each call (read or write) appends to a `trace: list[TraceEntry]` that the runner prints at the end. TraceEntry includes:
- step (an int counter starting at 1)
- tool_name
- parameters (a dict)
- decision (ALLOW / BLOCK / NA for reads)
- unsat_core (list of rule IDs, empty for ALLOW or NA)
- explanation (str, empty for ALLOW or NA)
- result_summary (a short string describing what happened, e.g. "refund R-001 created" or "blocked: rules R-3, R-9")

## Out of scope for tonight

- SQLite or any real persistence
- An actual LLM in the loop (the agent is a scripted Python list of tool calls)
- Audit log to file
- Multiple scenarios beyond the one demo
- The pre-deployment consistency check as a separate CLI (it runs implicitly when the policy is loaded; if the policy is unsat, the runner fails to start)

## Deliverables for Cursor

- `entities.py` — the four entity dataclasses plus `StateBundle`
- `seed_data.py` — the seed dicts above, function `load_db() -> dict` that returns a fresh DB
- `tools.py` — the two tool functions: `lookup_bundle` and `apply_refund` (the latter wraps the validator)
- `trace.py` — the `TraceEntry` dataclass, a `Trace` list-wrapper, and a `print_trace(trace)` helper that pretty-prints to stdout
