"""SQLite persistence for BioPyAI.

A workflow is the unit of saved work: one sequence with its metadata plus
one interpretation thread, in a single row. Conversations are stored as
JSON; the deterministic scan is not stored — it regenerates from the
sequence and window length on demand.

A fresh connection is opened per operation: fast enough for a single-user
local app, and it sidesteps sharing a connection across Streamlit reruns.
"""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

DB_PATH = Path(__file__).resolve().parent.parent / "biopyai.db"


def _connect():
    """Open a connection with rows accessible by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    """Current UTC time as a second-precision ISO string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db():
    """Create the workflows table if absent. Safe to call every run."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                seq_id        TEXT NOT NULL,
                description   TEXT,
                sequence      TEXT NOT NULL,
                organism      TEXT,
                molecule_type TEXT,
                source        TEXT,
                messages      TEXT,
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL
            )
            """
        )


def create_workflow(record, source, messages=None):
    """Insert a new workflow. Returns the new row id.

    messages is the conversation list, or None when no interpretation
    thread exists yet. It is JSON-encoded for storage.
    """
    now = _now()
    with closing(_connect()) as conn, conn:
        cursor = conn.execute(
            """
            INSERT INTO workflows
                (seq_id, description, sequence, organism,
                 molecule_type, source, messages, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.description,
                str(record.seq),
                record.annotations.get("organism"),
                record.annotations.get("molecule_type"),
                source,
                json.dumps(messages) if messages is not None else None,
                now,
                now,
            ),
        )
        return cursor.lastrowid


def list_workflows():
    """Return saved workflows, most recently updated first.

    Excludes the bulky sequence and messages columns: callers list a
    summary and fetch the full workflow only when one is opened.
    """
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT id, seq_id, description, organism,
                   molecule_type, source, created_at, updated_at
            FROM workflows
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()


def get_workflow(workflow_id):
    """Rebuild a saved workflow by id.

    Returns (SeqRecord, messages) where messages is the decoded
    conversation list (or None), or returns None if no such row exists.
    """
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM workflows WHERE id = ?", (workflow_id,)
        ).fetchone()

    if row is None:
        return None

    record = SeqRecord(
        Seq(row["sequence"]),
        id=row["seq_id"],
        description=row["description"] or "",
    )
    if row["organism"]:
        record.annotations["organism"] = row["organism"]
    if row["molecule_type"]:
        record.annotations["molecule_type"] = row["molecule_type"]

    messages = json.loads(row["messages"]) if row["messages"] else None
    return record, messages


def update_workflow(workflow_id, messages):
    """Overwrite a workflow's conversation and bump updated_at."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE workflows SET messages = ?, updated_at = ? "
            "WHERE id = ?",
            (json.dumps(messages) if messages is not None else None,
             _now(), workflow_id),
        )


def delete_workflow(workflow_id):
    """Remove a workflow permanently."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            "DELETE FROM workflows WHERE id = ?", (workflow_id,)
        )