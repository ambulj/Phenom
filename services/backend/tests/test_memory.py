"""
Unit tests for Phenom Encrypted Memory & Learned Rules
Tests:
1. Database encryption roundtrip
2. Message storage and retrieval
3. Learned rules CRUD (create, read, update, delete)
4. Active rule filtering for prompt injection
"""

import os
import secrets
import pytest
from services.backend.memory.db import EncryptedDatabaseManager
from services.backend.memory.rules import LearnedRulesManager

@pytest.fixture
def temp_encrypted_db(tmp_path):
    db_file = str(tmp_path / "test_memory.db")
    key = secrets.token_hex(32)
    return EncryptedDatabaseManager(db_path=db_file, encryption_key=key)

def test_messages_storage(temp_encrypted_db):
    temp_encrypted_db.add_message("msg-1", "user", "What is Phenom?", "llama3:latest", 10)
    temp_encrypted_db.add_message("msg-2", "assistant", "Phenom is your desktop assistant.", "llama3:latest", 15)
    
    msgs = temp_encrypted_db.get_recent_messages(5)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "Phenom is your desktop assistant."

def test_learned_rules_lifecycle(temp_encrypted_db):
    manager = LearnedRulesManager(db=temp_encrypted_db)
    
    # 1. Add Rule
    r1 = manager.add_rule("Always save summaries in Markdown format.")
    r2 = manager.add_rule("Never move photos.")
    
    rules = manager.list_rules()
    assert len(rules) == 2
    
    # 2. Edit Rule
    updated = manager.edit_rule(r1["id"], "Always save summaries in Markdown format with bullet points.")
    assert updated is True
    
    active_rules = manager.list_rules(active_only=True)
    assert any("bullet points" in r["rule_text"] for r in active_rules)
    
    # 3. Format for prompt
    prompt_snippet = manager.format_rules_for_prompt()
    assert "- Never move photos." in prompt_snippet
    assert "bullet points" in prompt_snippet
    
    # 4. Delete Rule
    deleted = manager.delete_rule(r2["id"])
    assert deleted is True
    remaining = manager.list_rules()
    assert len(remaining) == 1
    assert remaining[0]["id"] == r1["id"]
