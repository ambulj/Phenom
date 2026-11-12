"""
Unit tests for AST Safety Inspector (SYN-01, SAF-01).
Tests AST validation against Phenom Permanent Safety Rules and sandbox invariants.
"""

import pytest
from services.backend.safety.ast_inspector import ast_inspector


def test_safe_math_expression():
    code = """
def calculate_circle_area(radius: float) -> float:
    import math
    return math.pi * (radius ** 2)
"""
    report = ast_inspector.inspect_code(code)
    assert report.is_safe is True
    assert report.risk_tier == 0
    assert "CAP_MATH" in report.detected_capabilities
    assert len(report.violations) == 0
    assert "calculate_circle_area" in report.analyzed_functions


def test_safe_data_transform():
    code = """
def format_user_tags(raw_tags: list) -> dict:
    import json
    cleaned = [t.strip().lower() for t in raw_tags if t]
    return {"count": len(cleaned), "tags": cleaned}
"""
    report = ast_inspector.inspect_code(code)
    assert report.is_safe is True
    assert report.risk_tier == 0
    assert "CAP_DATA_TRANSFORM" in report.detected_capabilities
    assert len(report.violations) == 0


def test_banned_builtins_rejected():
    banned_snippets = [
        "eval('1 + 1')",
        "exec('x = 2')",
        "g = globals()",
        "l = locals()",
        "mod = __import__('os')",
        "breakpoint()",
        "inp = input('Enter:')",
        "val = getattr(obj, 'secret')",
        "setattr(obj, 'val', 10)",
        "delattr(obj, 'val')",
    ]
    for snippet in banned_snippets:
        report = ast_inspector.inspect_code(snippet)
        assert report.is_safe is False, f"Expected failure for: {snippet}"
        assert report.risk_tier == 3
        assert any(v.violation_type == "BANNED_BUILTIN" for v in report.violations)


def test_banned_modules_rejected():
    banned_imports = [
        "import socket",
        "import subprocess",
        "import ctypes",
        "import winreg",
        "import urllib.request",
        "import requests",
        "import http.client",
        "import aiohttp",
        "import httpx",
        "import multiprocessing",
        "from socket import create_connection",
        "from subprocess import Popen",
        "from shutil import rmtree",
    ]
    for snippet in banned_imports:
        report = ast_inspector.inspect_code(snippet)
        assert report.is_safe is False, f"Expected failure for: {snippet}"
        assert report.risk_tier == 3
        assert any(v.violation_type in ("BANNED_MODULE", "BANNED_SYMBOL_IMPORT") for v in report.violations)


def test_permanent_rule_7_permanent_delete_rejected():
    deletion_snippets = [
        "import os\nos.remove('file.txt')",
        "import os\nos.unlink('file.txt')",
        "import os\nos.rmdir('dir')",
        "from pathlib import Path\nPath('test.txt').unlink()",
        "from pathlib import Path\nPath('test_dir').rmdir()",
        "target.unlink()",
        "target.remove()",
        "shutil.rmtree('test_folder')",
    ]
    for snippet in deletion_snippets:
        report = ast_inspector.inspect_code(snippet)
        assert report.is_safe is False, f"Expected deletion failure for: {snippet}"
        assert report.risk_tier == 3
        assert any(v.violation_type in ("RULE_7_PERMANENT_DELETE_OR_EXEC", "BANNED_SYMBOL_IMPORT", "BANNED_MODULE") for v in report.violations)


def test_permanent_rule_8_payments_rejected():
    payment_snippets = [
        "def checkout_cart(cart_id: str): pass",
        "def pay_invoice(amount: float): pass",
        "def submit_credit_card(card_number: str): pass",
        "stripe = 'gateway'",
        "class PaymentProcessor:\n    pass",
        "result = obj.pay()",
        "result = obj.checkout()",
        "order.credit_card = '1234'",
    ]
    for snippet in payment_snippets:
        report = ast_inspector.inspect_code(snippet)
        assert report.is_safe is False, f"Expected payment failure for: {snippet}"
        assert report.risk_tier == 3
        assert any(v.violation_type == "RULE_8_PAYMENT_PRIMITIVE" for v in report.violations)


def test_reflection_escapes_rejected():
    reflection_snippets = [
        "subclasses = ().__class__.__bases__[0].__subclasses__()",
        "fn_code = my_func.__code__",
        "fn_globals = my_func.__globals__",
        "d = obj.__dict__",
        "cls = obj.__class__",
    ]
    for snippet in reflection_snippets:
        report = ast_inspector.inspect_code(snippet)
        assert report.is_safe is False, f"Expected reflection failure for: {snippet}"
        assert report.risk_tier == 3
        assert any(v.violation_type == "REFLECTION_ESCAPE" for v in report.violations)


def test_file_io_capability_and_tier_1_assignment():
    read_code = """
def read_log(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()
"""
    report = ast_inspector.inspect_code(read_code)
    assert report.is_safe is True
    assert report.risk_tier == 1
    assert "CAP_FILE_READ" in report.detected_capabilities

    write_code = """
def write_summary(path: str, content: str) -> int:
    with open(path, 'w') as f:
        return f.write(content)
"""
    report = ast_inspector.inspect_code(write_code)
    assert report.is_safe is True
    assert report.risk_tier == 1
    assert "CAP_FILE_WRITE" in report.detected_capabilities


def test_syntax_error_and_empty_code():
    bad_syntax = "def broken_func(:\n    pass"
    report = ast_inspector.inspect_code(bad_syntax)
    assert report.is_safe is False
    assert report.risk_tier == 3
    assert any(v.violation_type == "SYNTAX_ERROR" for v in report.violations)

    empty_report = ast_inspector.inspect_code("")
    assert empty_report.is_safe is False
    assert empty_report.risk_tier == 3
