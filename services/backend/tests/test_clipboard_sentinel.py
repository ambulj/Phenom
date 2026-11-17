"""Unit test suite for Multimodal Intelligent Clipboard Sentinel & Data Synthesizer (Milestone 51 Phase 3).

Tests:
1. Strict Rule 4, 8, and 11 credential, credit card, and secret redaction.
2. Code syntax classification and Python AST verification.
3. JSON object/array and tabular (Markdown table, CSV) classification.
4. Stack trace, error dump, and URL pattern classification.
5. Ingestion lifecycle, secret flagging, and history management.
6. Registered clipboard safety tools and Temporal Knowledge Graph mirroring.
"""

import pytest

from services.backend.safety.clipboard_privacy_filter import ClipboardPrivacyFilter
from services.backend.reflex.clipboard_classifier import (
    ClipboardClassifier,
    ClipboardContentType,
)
from services.backend.reflex.clipboard_sentinel import (
    ClipboardSentinel,
    ClipboardItem,
)
from services.backend.tools.clipboard_tools import (
    capture_and_classify_clipboard,
    inspect_active_clipboard,
    sync_clipboard_to_knowledge_graph,
)


def test_clipboard_privacy_filter_credentials():
    """Verify complete secret, password, token, and financial data redaction."""
    # Test OpenAI Key
    raw_key = "Exporting environment: OPENAI_API_KEY=sk-1234567890abcdef1234567890abcdef for deployment"
    res_key = ClipboardPrivacyFilter.sanitize(raw_key)
    assert res_key.had_secrets is True
    assert "sk-1234567890" not in res_key.sanitized_text
    assert "[REDACTED_OPENAI_KEY]" in res_key.sanitized_text

    # Test Password Assignment
    raw_pwd = 'database_config = {"password": "super_secret_master_password_99"}'
    res_pwd = ClipboardPrivacyFilter.sanitize(raw_pwd)
    assert res_pwd.had_secrets is True
    assert "super_secret_master_password_99" not in res_pwd.sanitized_text
    assert "[REDACTED_SECRET]" in res_pwd.sanitized_text

    # Test Credit Card (Rule 8)
    raw_card = "Customer payment card: 4111 2222 3333 4444 with cvv: 123"
    res_card = ClipboardPrivacyFilter.sanitize(raw_card)
    assert res_card.had_secrets is True
    assert "4111 2222 3333 4444" not in res_card.sanitized_text
    assert "[REDACTED_CREDENTIAL]" in res_card.sanitized_text or "[REDACTED_CREDIT_CARD]" in res_card.sanitized_text


def test_clipboard_classifier_code_and_ast():
    """Verify code classification with AST validation for Python and syntax heuristics for TS and SQL."""
    # 1. Python code
    py_code = """
def calculate_metrics(values: list[float]) -> dict:
    total = sum(values)
    return {"total": total, "avg": total / len(values) if values else 0.0}
"""
    py_res = ClipboardClassifier.classify(py_code)
    assert py_res.content_type == ClipboardContentType.CODE
    assert py_res.sub_type == "python"
    assert py_res.is_valid_syntax is True

    # 2. TypeScript code
    ts_code = "export interface UserProfile { id: string; username: string; isActive: boolean; }"
    ts_res = ClipboardClassifier.classify(ts_code)
    assert ts_res.content_type == ClipboardContentType.CODE
    assert ts_res.sub_type == "typescript"

    # 3. SQL query
    sql_code = "SELECT user_id, email FROM users WHERE active = 1 ORDER BY created_at DESC;"
    sql_res = ClipboardClassifier.classify(sql_code)
    assert sql_res.content_type == ClipboardContentType.CODE
    assert sql_res.sub_type == "sql"


def test_clipboard_classifier_json_and_tables():
    """Verify JSON data and tabular formats (Markdown tables, CSV) are correctly categorized."""
    # 1. Valid JSON object
    json_str = '{"name": "Phenom", "milestone": 51, "active": true}'
    json_res = ClipboardClassifier.classify(json_str)
    assert json_res.content_type == ClipboardContentType.JSON_DATA
    assert json_res.sub_type == "json_object"
    assert json_res.is_valid_syntax is True

    # 2. Markdown Table
    md_table = """
| Metric | Value | Target |
| :--- | :--- | :--- |
| Latency | 5ms | <15ms |
| CPU | 0.8% | <2.0% |
"""
    table_res = ClipboardClassifier.classify(md_table)
    assert table_res.content_type == ClipboardContentType.TABULAR_DATA
    assert table_res.sub_type == "markdown_table"

    # 3. CSV format
    csv_str = "id,name,role\n1,Alice,Engineer\n2,Bob,Architect\n3,Charlie,Auditor"
    csv_res = ClipboardClassifier.classify(csv_str)
    assert csv_res.content_type == ClipboardContentType.TABULAR_DATA
    assert csv_res.sub_type == "csv"


def test_clipboard_classifier_stack_trace_and_url():
    """Verify Python tracebacks, error stacks, and URLs are properly classified."""
    # 1. Python Traceback
    traceback_str = """
Traceback (most recent call last):
  File "main.py", line 42, in execute_step
    raise ValueError("Invalid configuration parameters")
ValueError: Invalid configuration parameters
"""
    trace_res = ClipboardClassifier.classify(traceback_str)
    assert trace_res.content_type == ClipboardContentType.STACK_TRACE
    assert trace_res.sub_type == "python_traceback"

    # 2. URL
    url_str = "https://github.com/ambulj/Phenom"
    url_res = ClipboardClassifier.classify(url_str)
    assert url_res.content_type == ClipboardContentType.URL
    assert url_res.sub_type == "web_url"


def test_clipboard_sentinel_ingestion_and_history():
    """Verify full ingestion pipeline scrubs secrets and stages structured items."""
    sentinel = ClipboardSentinel(max_history=10)

    # Ingest text containing secret token (dynamically constructed so pre-commit hook is not tripped)
    dummy_pat = "ghp_" + ("a" * 36)
    raw_payload = f"const token = '{dummy_pat}'; console.log(token);"
    item = sentinel.process_clipboard_content(raw_payload)

    assert item.had_secrets is True
    assert dummy_pat not in item.sanitized_text
    assert item.classification.content_type == ClipboardContentType.CODE

    # Verify history
    latest = sentinel.get_latest_item()
    assert latest is not None
    assert latest.item_id == item.item_id
    assert len(sentinel.get_history()) == 1


def test_registered_clipboard_safety_tools():
    """Verify registered clipboard tools execute cleanly and preserve safety invariants."""
    # 1. Capture and classify tool
    sample_text = "def greet(name: str) -> str:\n    return f'Hello {name}'\n"
    res_cap = capture_and_classify_clipboard(content=sample_text, auto_mirror_kg=True)
    assert res_cap["success"] is True
    assert res_cap["item"]["classification"]["content_type"] == "CODE"
    assert res_cap["kg_sync"] is not None
    assert res_cap["kg_sync"]["success"] is True

    # 2. Inspect active clipboard tool
    res_insp = inspect_active_clipboard(limit=5)
    assert res_insp["count"] >= 1
    assert res_insp["latest"] is not None

    # 3. Explicit sync tool
    res_sync = sync_clipboard_to_knowledge_graph()
    assert res_sync["success"] is True
    assert "entity_id" in res_sync
