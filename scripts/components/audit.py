#!/usr/bin/env python3
"""
AuditTrail — append-only, immutable audit log for skill migration sessions.

Each session creates an isolated directory under /tmp/skill-migration-{session_id}/.
Log entries are appended to audit.jsonl and are never modified after writing.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Action(str, Enum):
    """Allowed migration actions — each log entry records one of these."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    RENAME = "rename"
    MOVE = "move"
    VALIDATE = "validate"
    SPLIT = "split"


class AuditTrail:
    """Append-only audit log for a single skill migration session."""

    def __init__(self, session_id: Optional[str] = None):
        if session_id is None:
            session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        self.session_id = session_id
        self.base_dir = f"/tmp/skill-migration-{session_id}"
        self._ensure_dirs()

    # ── helpers ──

    def _ensure_dirs(self):
        os.makedirs(f"{self.base_dir}/snapshots", exist_ok=True)
        os.makedirs(f"{self.base_dir}/reports", exist_ok=True)

    # ── public API ──

    def log(self, phase: str, action: Action, target: str,
            source_hash: str = "", decision: Optional[dict] = None,
            approval: bool = True,
            blocked_by: Optional[list] = None) -> str:
        """Append one immutable JSON line to audit.jsonl. Returns trace_id."""
        entry = {
            "trace_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "action": action.value if isinstance(action, Action) else action,
            "target": target,
            "source_hash": source_hash,
            "decision": decision or {},
            "approval": approval,
            "blocked_by": blocked_by or [],
        }
        trail_path = f"{self.base_dir}/audit.jsonl"
        with open(trail_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry["trace_id"]

    def snapshot(self, phase_number: int, registry_data: dict):
        """Write a full JSON snapshot of registry state at a given phase."""
        path = f"{self.base_dir}/snapshots/phase-{phase_number}-registry.json"
        with open(path, "w") as f:
            json.dump(registry_data, f, indent=2, ensure_ascii=False)

    def report(self, name: str, content: str):
        """Write a markdown report under reports/{name}.md."""
        path = f"{self.base_dir}/reports/{name}.md"
        with open(path, "w") as f:
            f.write(content)

    def git_log(self, commit_sha: str):
        """Append a commit SHA to git-log.txt (one per line)."""
        path = f"{self.base_dir}/git-log.txt"
        with open(path, "a") as f:
            f.write(commit_sha + "\n")
