"""WFM → registry e2e orchestration (G1 wiring + G2 loop). See ``development_plan_g1_g2_orchestration.md``."""

from wfm_orchestration.orchestrator import run_wfm_registry_e2e
from wfm_orchestration.snapshot_from_agents import wfm_acceptance_snapshot_from_agent_outputs

__all__ = ["run_wfm_registry_e2e", "wfm_acceptance_snapshot_from_agent_outputs"]
