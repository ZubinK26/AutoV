from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal

from agentsim.runtime.models import AuditDecision, AuditLogEntry


def append_audit(conn: sqlite3.Connection, entry: AuditLogEntry) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (
            interaction_id, timestamp, tool_name, parameters_json, decision,
            unsat_core_json, explanation, policy_version, rules_consulted_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry.interaction_id,
            entry.timestamp.isoformat(),
            entry.tool_name,
            json.dumps(entry.parameters),
            entry.decision,
            json.dumps(entry.unsat_core) if entry.unsat_core is not None else None,
            entry.explanation,
            entry.policy_version,
            json.dumps(entry.rules_consulted),
        ),
    )
    conn.commit()
