"""SQLite persistence for BioPyAI.

Stores loaded sequences so they can be reopened across sessions. A fresh
connection is opened per operation: fast enough for a single-user local
app, and it avoids sharing a connection across Streamlit's reruns.
"""

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


def init_db():
    """Create tables if absent. Safe to call on every run."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sequences (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                seq_id        TEXT NOT NULL,
                description   TEXT,
                sequence      TEXT NOT NULL,
                organism      TEXT,
                molecule_type TEXT,
                source        TEXT,
                created_at    TEXT NOT NULL
            )
            """
        )


def save_sequence(record, source):
    """Persist a SeqRecord. Returns the new row id."""
    with closing(_connect()) as conn, conn:
        cursor = conn.execute(
            """
            INSERT INTO sequences
                (seq_id, description, sequence, organism,
                 molecule_type, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.description,
                str(record.seq),
                record.annotations.get("organism"),
                record.annotations.get("molecule_type"),
                source,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        return cursor.lastrowid


def list_sequences():
    """Return saved sequences, newest first, as a list of rows."""
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT id, seq_id, description, organism,
                   molecule_type, source, created_at
            FROM sequences
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()


def get_sequence(row_id):
    """Rebuild a SeqRecord from a saved row, or None if not found."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM sequences WHERE id = ?", (row_id,)
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
    return record