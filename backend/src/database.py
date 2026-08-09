import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), "caller_memory.db")

def init_db():
    """Initialize the database with the caller memory table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table for caller memory
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS caller_memory (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            language_preference TEXT DEFAULT 'en',
            facts TEXT,  -- JSON string
            last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def get_caller(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve caller information from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, name, language_preference, facts, last_interaction, created_at
        FROM caller_memory
        WHERE user_id = ?
    ''', (user_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        user_id, name, language_preference, facts_json, last_interaction, created_at = row
        facts = json.loads(facts_json) if facts_json else {}

        return {
            "user_id": user_id,
            "name": name,
            "language_preference": language_preference,
            "facts": facts,
            "last_interaction": last_interaction,
            "created_at": created_at
        }

    return None

def save_caller(user_id: str, name: str, language_preference: str = "en",
                facts: Dict[str, Any] = None) -> bool:
    """Save or update caller information in the database."""
    if facts is None:
        facts = {}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # JSON serialize facts
    facts_json = json.dumps(facts)
    now = datetime.now().isoformat()

    # Upsert operation (INSERT or UPDATE)
    cursor.execute('''
        INSERT INTO caller_memory (user_id, name, language_preference, facts, last_interaction)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            name = excluded.name,
            language_preference = excluded.language_preference,
            facts = excluded.facts,
            last_interaction = excluded.last_interaction
    ''', (user_id, name, language_preference, facts_json, now))

    conn.commit()
    conn.close()

    return True

def update_last_interaction(user_id: str) -> bool:
    """Update the last_interaction timestamp for a caller."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE caller_memory
        SET last_interaction = ?
        WHERE user_id = ?
    ''', (now, user_id))

    conn.commit()
    affected_rows = cursor.rowcount
    conn.close()

    return affected_rows > 0

def delete_caller(user_id: str) -> bool:
    """Delete a caller from the database (for 'forget me' functionality)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM caller_memory
        WHERE user_id = ?
    ''', (user_id,))

    conn.commit()
    affected_rows = cursor.rowcount
    conn.close()

    return affected_rows > 0

# Initialize database when module is loaded
init_db()