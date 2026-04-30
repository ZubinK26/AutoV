from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agentsim.runtime.policy_source import resolve_z3_policy_text

from agentsim.runtime.clock import NowFn, utc_now
from agentsim.runtime.db import load_builtin_seed, load_seed_path, open_memory_db
from agentsim.runtime.models import Channel
from agentsim.runtime.read_tools import ReadToolExecutor
from agentsim.runtime.snapshot import full_snapshot_builder
from agentsim.runtime.validator_stub import always_allow_validate
from agentsim.runtime.write_tools import SnapshotFn, WriteToolExecutor, ValidateFn
from agentsim.runtime.z3_legality import Z3LegalityChecker, make_z3_policy_validate


@dataclass
class ScenarioContext:
    conn: sqlite3.Connection
    interaction_id: str
    read_tools: ReadToolExecutor
    write_tools: WriteToolExecutor


class ScenarioHarness:
    """Fresh DB + seed + interaction; read / write sessions through Slice E."""

    def __init__(self, *, clock: NowFn | None = None, policy_version: str = "slice-a") -> None:
        self.clock = clock or utc_now
        self.policy_version = policy_version

    def fresh_connection(
        self,
        seed: Literal["builtin"] | Path | str = "builtin",
    ) -> sqlite3.Connection:
        conn = open_memory_db()
        if seed == "builtin":
            load_builtin_seed(conn)
        else:
            load_seed_path(conn, Path(seed))
        return conn

    def create_interaction(
        self,
        conn: sqlite3.Connection,
        *,
        customer_id: str,
        channel: Channel = Channel.CHAT,
    ) -> str:
        interaction_id = f"I-{uuid.uuid4().hex[:10]}"
        started = self.clock()
        conn.execute(
            """
            INSERT INTO interaction (
                interaction_id, customer_id, channel, started_at,
                actions_taken_json, escalated_to_human
            ) VALUES (?, ?, ?, ?, '[]', 0)
            """,
            (interaction_id, customer_id, channel.value, started.isoformat()),
        )
        conn.commit()
        return interaction_id

    def open_read_session(
        self,
        conn: sqlite3.Connection,
        interaction_id: str,
    ) -> ReadToolExecutor:
        return ReadToolExecutor(
            conn,
            interaction_id=interaction_id,
            policy_version=self.policy_version,
            clock=self.clock,
        )

    def open_write_session(
        self,
        conn: sqlite3.Connection,
        interaction_id: str,
        *,
        validate_call: ValidateFn | None = None,
        build_snapshot: SnapshotFn | None = None,
        repeated_block_limit: int | None = None,
    ) -> WriteToolExecutor:
        return WriteToolExecutor(
            conn,
            interaction_id=interaction_id,
            policy_version=self.policy_version,
            clock=self.clock,
            validate_call=validate_call or always_allow_validate,
            build_snapshot=build_snapshot,
            repeated_block_limit=repeated_block_limit,
        )

    def begin_scenario(
        self,
        *,
        seed: Literal["builtin"] | Path | str = "builtin",
        customer_id: str,
        channel: Channel = Channel.CHAT,
        validate_call: ValidateFn | None = None,
        build_snapshot: SnapshotFn | None = None,
        use_builtin_z3_policy: bool = False,
        policy_smt2_path: Path | str | None = None,
        policy_smt2_text: str | None = None,
        repeated_block_limit: int | None = None,
    ) -> ScenarioContext:
        conn = self.fresh_connection(seed)
        iid = self.create_interaction(conn, customer_id=customer_id, channel=channel)
        reads = self.open_read_session(conn, iid)
        v_fn = validate_call
        b_fn = build_snapshot
        if use_builtin_z3_policy:
            if v_fn is not None or b_fn is not None:
                msg = "use_builtin_z3_policy is exclusive with validate_call / build_snapshot"
                raise ValueError(msg)
            policy_text = resolve_z3_policy_text(
                policy_smt2_path=policy_smt2_path,
                policy_smt2_text=policy_smt2_text,
            )
            checker = Z3LegalityChecker(policy_text)
            v_fn = make_z3_policy_validate(checker)
            b_fn = full_snapshot_builder(conn, interaction_id=iid)
        writes = self.open_write_session(
            conn,
            iid,
            validate_call=v_fn,
            build_snapshot=b_fn,
            repeated_block_limit=repeated_block_limit,
        )
        return ScenarioContext(conn=conn, interaction_id=iid, read_tools=reads, write_tools=writes)

    def begin_scenario_always_allow_full_snapshots(
        self,
        *,
        seed: Literal["builtin"] | Path | str = "builtin",
        customer_id: str,
        channel: Channel = Channel.CHAT,
        repeated_block_limit: int | None = None,
    ) -> ScenarioContext:
        """Vanilla executor path: always ALLOW, full DB snapshots (for post-hoc policy replay)."""

        conn = self.fresh_connection(seed)
        iid = self.create_interaction(conn, customer_id=customer_id, channel=channel)
        reads = self.open_read_session(conn, iid)
        b_fn = full_snapshot_builder(conn, interaction_id=iid)
        writes = self.open_write_session(
            conn,
            iid,
            validate_call=always_allow_validate,
            build_snapshot=b_fn,
            repeated_block_limit=repeated_block_limit,
        )
        return ScenarioContext(conn=conn, interaction_id=iid, read_tools=reads, write_tools=writes)
