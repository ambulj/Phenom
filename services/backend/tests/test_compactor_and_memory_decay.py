"""
Unit tests for Memory Compactor and Spaced Relevance Fact Decay.
"""

import sqlite3
from datetime import datetime, timezone, timedelta
import pytest
from services.backend.memory.compactor import MemoryCompactor

def test_compactor_should_compact():
    compactor = MemoryCompactor(max_turns=10)
    
    short_history = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
    assert not compactor.should_compact(short_history)

    long_history = [{"role": "user", "content": f"msg {i}"} for i in range(12)]
    assert compactor.should_compact(long_history)

    huge_message = [{"role": "user", "content": "x" * 25000}]
    assert compactor.should_compact(huge_message, token_limit=5000)

def test_compactor_compact_history():
    compactor = MemoryCompactor(max_turns=10, preserve_recent=4)

    messages = [
        {"role": "user", "content": "I prefer using dark mode."},
        {"role": "assistant", "content": "Understood, dark mode enabled."},
        {"role": "user", "content": "My nickname is Abhi and I code in Python."},
        {"role": "assistant", "content": "Great to know, Abhi."},
        {"role": "user", "content": "Let's work on task 1."},
        {"role": "assistant", "content": "Task 1 ready."},
        {"role": "user", "content": "Now run the tests."},
        {"role": "assistant", "content": "Tests passing."},
        {"role": "user", "content": "Check coverage."},
        {"role": "assistant", "content": "Coverage is 95%."}
    ]

    result = compactor.compact_history(messages)
    assert result.compacted_count == 6
    assert len(result.preserved_messages) == 4
    assert result.preserved_messages[0]["content"] == "Now run the tests."
    assert len(result.extracted_facts) >= 1
    assert any("dark mode" in f.lower() or "abhi" in f.lower() for f in result.extracted_facts)
    assert "Prior conversation summary:" in result.context_summary

def test_fact_retention_rules():
    compactor = MemoryCompactor(decay_days=14)
    now = datetime.now(timezone.utc)
    old_date = (now - timedelta(days=20)).isoformat()
    recent_date = (now - timedelta(days=5)).isoformat()

    # Permanent categories are always retained
    assert compactor.evaluate_fact_retention("profile", "Owner likes tea", old_date)
    assert compactor.evaluate_fact_retention("preference", "Theme is dark", old_date)
    assert compactor.evaluate_fact_retention("owner", "Nickname is Abhi", old_date)

    # Transient categories decay if older than 14 days
    assert not compactor.evaluate_fact_retention("transient", "Temporary scratchpad", old_date)
    assert compactor.evaluate_fact_retention("transient", "Recent note", recent_date)

def test_prune_decayed_facts_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
    CREATE TABLE facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        fact TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=25)).isoformat()
    recent_ts = (now - timedelta(days=2)).isoformat()

    conn.execute("INSERT INTO facts (category, fact, created_at) VALUES (?, ?, ?);",
                 ("profile", "Owner nickname Abhi", old_ts))
    conn.execute("INSERT INTO facts (category, fact, created_at) VALUES (?, ?, ?);",
                 ("scratch", "Old temporary buffer", old_ts))
    conn.execute("INSERT INTO facts (category, fact, created_at) VALUES (?, ?, ?);",
                 ("scratch", "Fresh temporary buffer", recent_ts))
    conn.commit()

    compactor = MemoryCompactor(decay_days=14)
    pruned = compactor.prune_decayed_facts(conn)
    assert pruned == 1

    cursor = conn.cursor()
    cursor.execute("SELECT fact FROM facts;")
    remaining = [row[0] for row in cursor.fetchall()]
    assert "Owner nickname Abhi" in remaining
    assert "Fresh temporary buffer" in remaining
    assert "Old temporary buffer" not in remaining
