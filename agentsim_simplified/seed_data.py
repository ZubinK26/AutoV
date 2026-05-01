from __future__ import annotations

from typing import Any

from agentsim_simplified.entities import Account, Customer, Transaction

DBShape = dict[str, dict[str, Any]]


def load_db() -> DBShape:
    """Fresh in-memory DB per 01_simulation_environment_simpl.md."""

    customers: dict[str, Customer] = {
        "C-001": Customer("C-001", "VERIFIED", False, 0),
        "C-002": Customer("C-002", "VERIFIED", True, 0),
        "C-003": Customer("C-003", "VERIFIED", False, 49500),
        "C-004": Customer("C-004", "FAILED", False, 0),
        "C-005": Customer("C-005", "VERIFIED", False, 0),
    }
    accounts: dict[str, Account] = {
        "A-001": Account("A-001", "C-001", "ACTIVE", False),
        "A-002": Account("A-002", "C-002", "ACTIVE", False),
        "A-003": Account("A-003", "C-003", "ACTIVE", False),
        "A-004": Account("A-004", "C-004", "ACTIVE", False),
        "A-005": Account("A-005", "C-005", "ACTIVE", True),
    }
    transactions: dict[str, Transaction] = {
        "T-001": Transaction("T-001", "A-001", 5000, "POSTED"),
        "T-002": Transaction("T-002", "A-002", 30000, "POSTED"),
        "T-003": Transaction("T-003", "A-003", 2000, "POSTED"),
        "T-004": Transaction("T-004", "A-004", 4000, "POSTED"),
        "T-005": Transaction("T-005", "A-005", 6000, "POSTED"),
        "T-006": Transaction("T-006", "A-001", 8000, "POSTED"),
        "T-007": Transaction("T-007", "A-001", 1500, "PENDING"),
    }
    return {"customers": customers, "accounts": accounts, "transactions": transactions, "refunds": {}}
