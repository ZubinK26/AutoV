"""bundle_id / rule_id generation (`dev_plan_implementation_control_flow_v3.md`)."""

from __future__ import annotations

import uuid


def new_bundle_id() -> str:
    return "b_" + uuid.uuid4().hex[:16]


def new_rule_id() -> str:
    return "r_" + uuid.uuid4().hex[:12]
