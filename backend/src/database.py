import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), "caller_memory.db")


def _ensure_column(cursor: sqlite3.Cursor, table: str, column_def: str) -> None:
    column_name = column_def.split()[0]
    cursor.execute(f"PRAGMA table_info({table})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def init_db():
    """Initialize the database with the caller memory table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table for caller memory
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS caller_memory (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            language_preference TEXT DEFAULT 'en',
            escalation_reference TEXT,
            facts TEXT,  -- JSON string
            last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Backfill schema changes for older installs.
    _ensure_column(cursor, "caller_memory", "escalation_reference TEXT")
    _ensure_column(cursor, "caller_memory", "facts TEXT")
    _ensure_column(
        cursor,
        "caller_memory",
        "last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    )
    _ensure_column(
        cursor,
        "caller_memory",
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    )
    _ensure_column(
        cursor,
        "caller_memory",
        "language_preference TEXT DEFAULT 'en'",
    )

    # Create table for escalations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            summary TEXT,
            urgency TEXT,
            language TEXT,
            status TEXT DEFAULT 'open',
            human_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_caller(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve caller information from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT user_id, name, language_preference, escalation_reference, facts, last_interaction, created_at
        FROM caller_memory
        WHERE user_id = ?
    """,
        (user_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        (
            user_id,
            name,
            language_preference,
            escalation_reference,
            facts_json,
            last_interaction,
            created_at,
        ) = row
        facts = json.loads(facts_json) if facts_json else {}

        return {
            "user_id": user_id,
            "name": name,
            "language_preference": language_preference,
            "escalation_reference": escalation_reference,
            "facts": facts,
            "last_interaction": last_interaction,
            "created_at": created_at,
        }

    return None


def find_caller(identifier: str) -> Optional[Dict[str, Any]]:
    """Find caller information by user_id, name, or escalation reference."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    identifier = (identifier or "").strip()
    if not identifier:
        conn.close()
        return None

    cursor.execute(
        """
        SELECT user_id, name, language_preference, escalation_reference, facts, last_interaction, created_at
        FROM caller_memory
        WHERE user_id = ?
           OR name = ?
           OR escalation_reference = ?
           OR facts LIKE ?
        ORDER BY last_interaction DESC
        LIMIT 1
    """,
        (identifier, identifier, identifier, f'%"{identifier}"%'),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    facts = json.loads(row["facts"]) if row["facts"] else {}
    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "language_preference": row["language_preference"],
        "escalation_reference": row["escalation_reference"],
        "facts": facts,
        "last_interaction": row["last_interaction"],
        "created_at": row["created_at"],
    }


def save_caller(
    user_id: str,
    name: str,
    language_preference: str = "en",
    facts: Dict[str, Any] = None,
    escalation_reference: str | None = None,
) -> bool:
    """Save or update caller information in the database."""
    if facts is None:
        facts = {}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # JSON serialize facts
    facts_json = json.dumps(facts)
    now = datetime.now().isoformat()

    # Upsert operation (INSERT or UPDATE)
    cursor.execute(
        """
        INSERT INTO caller_memory (user_id, name, language_preference, escalation_reference, facts, last_interaction)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            name = excluded.name,
            language_preference = excluded.language_preference,
            escalation_reference = COALESCE(excluded.escalation_reference, caller_memory.escalation_reference),
            facts = excluded.facts,
            last_interaction = excluded.last_interaction
    """,
        (user_id, name, language_preference, escalation_reference, facts_json, now),
    )

    conn.commit()
    conn.close()

    return True


def update_last_interaction(user_id: str) -> bool:
    """Update the last_interaction timestamp for a caller."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    cursor.execute(
        """
        UPDATE caller_memory
        SET last_interaction = ?
        WHERE user_id = ?
    """,
        (now, user_id),
    )

    conn.commit()
    affected_rows = cursor.rowcount
    conn.close()

    return affected_rows > 0


def delete_caller(user_id: str) -> bool:
    """Delete a caller from the database (for 'forget me' functionality)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM caller_memory
        WHERE user_id = ?
    """,
        (user_id,),
    )

    conn.commit()
    affected_rows = cursor.rowcount
    conn.close()

    return affected_rows > 0


import uuid


def create_escalation(user_id: str, summary: str, urgency: str, language: str) -> str:
    """Create a new escalation request and return its reference ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Generate a short, readable reference ID
    ref_id = "REQ-" + str(uuid.uuid4())[:6].upper()

    cursor.execute(
        """
        INSERT INTO escalations (id, user_id, summary, urgency, language)
        VALUES (?, ?, ?, ?, ?)
    """,
        (ref_id, user_id, summary, urgency, language),
    )

    conn.commit()
    conn.close()

    return ref_id


def get_escalations() -> list:
    """Retrieve all escalations."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, user_id, summary, urgency, language, status, human_response, created_at
        FROM escalations
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_escalation(
    escalation_id: str, status: str, human_response: str = None
) -> bool:
    """Update an escalation's status and response."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE escalations
        SET status = ?, human_response = COALESCE(?, human_response)
        WHERE id = ?
    """,
        (status, human_response, escalation_id),
    )

    conn.commit()
    affected_rows = cursor.rowcount
    conn.close()

    return affected_rows > 0


def get_escalation_status(escalation_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a specific escalation."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, status, human_response
        FROM escalations
        WHERE id = ?
    """,
        (escalation_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


# Initialize database when module is loaded
init_db()
