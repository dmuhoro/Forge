"""Forge orchestrator core — the deterministic task layer under the agents.

Implements the 2026-09-05 build-brief step 1 ("Task schema + state machine, zero AI"):
an append-only task journal drives Planner→Builder→Reviewer with a fail-closed gate.
Pure stdlib, no network, no AI — the agent roles plug in later against these same
types and rules. Alignment: ShrinkMedia ADR-014 (ForgeTask semantics) + brief §2 schema.
"""

__version__ = "0.3.0"

from .task import Task, TaskInput, MAX_ATTEMPTS, Status, StatusRefusal
from .engine import engine, valid_from, allowed_transitions
from .journal import Journal
from .corpus import REPO_ROOT, CorpusRefusal, load, match, validate, verify_citations
from .dash import DashRefusal, ecosystem_board, project_board

__all__ = [
    "Task",
    "TaskInput",
    "MAX_ATTEMPTS",
    "Status",
    "StatusRefusal",
    "engine",
    "valid_from",
    "allowed_transitions",
    "Journal",
    "REPO_ROOT",
    "CorpusRefusal",
    "load",
    "match",
    "validate",
    "verify_citations",
    "DashRefusal",
    "project_board",
    "ecosystem_board",
]