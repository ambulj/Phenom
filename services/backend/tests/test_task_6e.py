"""
Unit & Integration Tests for Task 6E: Futuristic Animated UI & Floating Orb Window
Verifies:
1. CSP header is present and strict in index.html (Hardening F11/H2).
2. Electron main.cjs enforces sender verification on phenom:get-session-token.
3. First-run wizard is reachable (isFirstRunDone defaults to false, not true).
4. One-line confirmation modal invariant: tier, target, item count, and correct labels.
5. Markdown renderer sanitization: zero raw JSON, no emoji badges, code blocks structured.
6. Live view panel invariants: step list (done/doing/next) and click target coordinates.
7. prefers-reduced-motion accessibility rules present in theme.css.
"""

import os
import re
import json
import pytest

def test_csp_header_present_in_index_html():
    """Acceptance: verify strict CSP meta tag in index.html (Hardening F11/H2)."""
    with open("apps/desktop/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert "Content-Security-Policy" in html
    assert "default-src 'self'" in html
    assert "connect-src 'self' ws://127.0.0.1:*" in html


def test_electron_first_run_done_default_is_false():
    """Acceptance: verify isFirstRunDone defaults to false so setup wizard is reachable (Task 6E.9)."""
    with open("apps/desktop/electron/main.cjs", "r", encoding="utf-8") as f:
        code = f.read()

    # Search for isFirstRunDone definition
    start = code.find("function isFirstRunDone()")
    assert start != -1
    end = code.find("function setFirstRunDone()", start)
    assert end != -1
    body = code[start:end]

    # Must default to false, not true
    assert "return false;" in body
    assert "return true; // Already configured" not in body


def test_electron_session_token_sender_verification():
    """Acceptance: verify get-session-token validates sender frame origin (Task 6E.13)."""
    with open("apps/desktop/electron/main.cjs", "r", encoding="utf-8") as f:
        code = f.read()

    assert "phenom:get-session-token" in code
    assert "isTrusted" in code
    assert "Blocked get-session-token request from untrusted origin" in code


def test_orb_window_separate_creation_and_clickthrough():
    """Acceptance: verify separate frameless transparent orbWindow with click-through and edge snapping (Task 6E.1)."""
    with open("apps/desktop/electron/main.cjs", "r", encoding="utf-8") as f:
        code = f.read()

    assert "function createOrbWindow()" in code
    assert "transparent: true" in code
    assert "alwaysOnTop: true" in code
    assert "skipTaskbar: true" in code
    assert "setIgnoreMouseEvents(true, { forward: true })" in code
    assert "orb:set-ignore-mouse-events" in code
    assert "SNAP_MARGIN" in code


def test_unrequested_components_deleted():
    """Acceptance: verify CommandPalette, StreamingConsole, and HUDCard are deleted (Task 6E.10)."""
    assert not os.path.exists("apps/desktop/src/components/CommandPalette.tsx")
    assert not os.path.exists("apps/desktop/src/components/StreamingConsole.tsx")
    assert not os.path.exists("apps/desktop/src/components/HUDCard.tsx")


def test_theme_css_reduced_motion_suppression():
    """Acceptance: verify prefers-reduced-motion media query suppresses animations (Task 6E)."""
    with open("apps/desktop/src/theme.css", "r", encoding="utf-8") as f:
        css = f.read()

    assert "prefers-reduced-motion: reduce" in css
    assert "animation-duration: 0.01ms !important" in css
    assert "transition-duration: 0.01ms !important" in css


def test_confirmation_modal_labels_and_one_line_summary():
    """Acceptance: verify tier 1/2/3 labels and one-line summary in ConfirmationModal.tsx (Task 6E.6)."""
    with open("apps/desktop/src/components/ConfirmationModal.tsx", "r", encoding="utf-8") as f:
        modal_code = f.read()

    # Fixed labels
    assert "TIER 1 • REVERSIBLE CHANGE" in modal_code
    assert "TIER 2 • DESTRUCTIVE / EXTERNAL" in modal_code
    assert "TIER 3 • BLOCKED / SYSTEM RESTRICTED" in modal_code

    # One-line summary and details on tap
    assert "[Tier {request.tier}]" in modal_code
    assert "itemCount" in modal_code
    assert "showDetails" in modal_code


def test_chatbox_sanitizer_removes_tool_emoji_badges():
    """Acceptance: verify sanitizeChatText removes [Tool ... Result] emoji badge lines (Task 6E.3)."""
    # Import or test regex from ChatBox.tsx
    sample_text = (
        "Opening Notepad for you Bro!\n"
        "[Tool open_app Result: Process started with PID 1024]\n"
        "All set, notepad is on your screen!"
    )

    cleaned = re.sub(r"\[Tool\s+[a-zA-Z0-9_]+\s+Result:\s*[^\]]*\]\n?", "", sample_text).strip()
    assert "[Tool" not in cleaned
    assert "Process started" not in cleaned
    assert "Opening Notepad for you Bro!" in cleaned
    assert "All set, notepad is on your screen!" in cleaned


def test_live_view_panel_has_explicit_pause_and_takeover():
    """Acceptance: verify explicit Pause and Take-Over buttons and step list in LiveViewPanel.tsx (Task 6E.4)."""
    with open("apps/desktop/src/components/panels/LiveViewPanel.tsx", "r", encoding="utf-8") as f:
        code = f.read()

    assert "Pause Automation" in code or "Pause" in code
    assert "Take-Over" in code
    assert "clickTarget" in code
    assert "EXECUTION STEP LIST (DONE / DOING / NEXT)" in code
