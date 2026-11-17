"""Unit test suite for Active Desktop Focus & Contextual Semantic Anchor (Milestone 51 Phase 4).

Tests:
1. Application executable classification into semantic categories.
2. IDE window title parsing for active file and project names.
3. Proposal generation for test failure events.
4. Proposal generation for build failures with active file target.
5. Proposal generation correlating clipboard items with active workspace.
6. Focus Guard target window verification and divergence protection.
7. Registered contextual anchor safety tools.
"""

import pytest

from services.backend.schemas.semantic_focus import WindowContext, BoundingRect
from services.backend.schemas.reflex_events import ReflexEvent, ReflexEventType, ReflexSeverity
from services.backend.desktop.window_focus_tracker import WindowFocusTracker
from services.backend.reflex.contextual_anchor import (
    ContextualAnchorManager,
    ActiveContextAnchor,
    ApplicationCategory,
)
from services.backend.reflex.action_suggester import (
    ContextualActionSuggester,
    ContextualProposal,
)
from services.backend.reflex.clipboard_sentinel import ClipboardItem
from services.backend.reflex.clipboard_classifier import ClassifiedClipboardPayload, ClipboardContentType
from services.backend.tools.contextual_anchor_tools import (
    resolve_active_context_anchor,
    generate_contextual_action_proposals,
    validate_target_window_focus,
)


def test_contextual_anchor_categorization():
    """Verify application executable mapping into ApplicationCategory."""
    mgr = ContextualAnchorManager()

    assert mgr.categorize_process("Code.exe") == ApplicationCategory.IDE
    assert mgr.categorize_process("cursor.exe") == ApplicationCategory.IDE
    assert mgr.categorize_process("WindowsTerminal.exe") == ApplicationCategory.TERMINAL
    assert mgr.categorize_process("pwsh.exe") == ApplicationCategory.TERMINAL
    assert mgr.categorize_process("chrome.exe") == ApplicationCategory.BROWSER
    assert mgr.categorize_process("msedge.exe") == ApplicationCategory.BROWSER
    assert mgr.categorize_process("excel.exe") == ApplicationCategory.OFFICE_DOCUMENT
    assert mgr.categorize_process("Telegram.exe") == ApplicationCategory.COMMUNICATION
    assert mgr.categorize_process("notepad.exe") == ApplicationCategory.OTHER


def test_ide_title_parsing():
    """Verify title parsing extracts active file and project workspace."""
    mgr = ContextualAnchorManager()

    # Standard VS Code format
    file1, proj1 = mgr.parse_ide_title("main.py - Phenom - Visual Studio Code")
    assert file1 == "main.py"
    assert proj1 == "Phenom"

    # Dirty marker / bullet format
    file2, proj2 = mgr.parse_ide_title("App.tsx • Phenom - Visual Studio Code")
    assert file2 == "App.tsx"
    assert proj2 == "Phenom"

    # Generic title without file
    file3, proj3 = mgr.parse_ide_title("Phenom - Visual Studio Code")
    assert file3 is None


def test_proposal_generation_for_test_failure():
    """Verify test failures generate diagnostic re-run proposal."""
    tracker = WindowFocusTracker()
    tracker.set_simulated_window(WindowContext(
        hwnd=1001,
        title="pwsh.exe - C:\\Phenom",
        process_name="WindowsTerminal.exe",
        pid=5555,
        bounding_rect=BoundingRect(left=0, top=0, right=1920, bottom=1080),
    ))
    suggester = ContextualActionSuggester(tracker=tracker)
    anchor = suggester.anchor_mgr.resolve_anchor()

    ev_fail = ReflexEvent(
        event_type=ReflexEventType.TESTS_FAILED,
        severity=ReflexSeverity.CRITICAL,
    )

    proposals = suggester.generate_proposals(anchor=anchor, event=ev_fail)
    assert len(proposals) >= 1
    p = proposals[0]
    assert "Re-run" in p.title
    assert p.target_hwnd == 1001
    assert p.target_process == "WindowsTerminal.exe"
    assert p.tier in (0, 1)


def test_proposal_generation_for_build_failure():
    """Verify build failure targets active editing file for automated review."""
    tracker = WindowFocusTracker()
    tracker.set_simulated_window(WindowContext(
        hwnd=2002,
        title="dag_planner.py - Phenom - Visual Studio Code",
        process_name="Code.exe",
        pid=6666,
        bounding_rect=BoundingRect(left=0, top=0, right=1920, bottom=1080),
    ))
    suggester = ContextualActionSuggester(tracker=tracker)
    anchor = suggester.anchor_mgr.resolve_anchor()
    assert anchor.active_file == "dag_planner.py"

    ev_build = ReflexEvent(
        event_type=ReflexEventType.BUILD_FAILED,
        severity=ReflexSeverity.CRITICAL,
    )

    proposals = suggester.generate_proposals(anchor=anchor, event=ev_build)
    assert len(proposals) >= 1
    p = next(prop for prop in proposals if "Inspect" in prop.title)
    assert p.tool_name == "read_file"
    assert p.tool_args["path"] == "dag_planner.py"
    assert p.tier == 0


def test_proposal_generation_for_clipboard_data():
    """Verify JSON or code on clipboard triggers formatting / insertion proposals."""
    tracker = WindowFocusTracker()
    tracker.set_simulated_window(WindowContext(
        hwnd=3003,
        title="settings.json - Phenom - Visual Studio Code",
        process_name="Code.exe",
        pid=7777,
        bounding_rect=BoundingRect(left=0, top=0, right=1920, bottom=1080),
    ))
    suggester = ContextualActionSuggester(tracker=tracker)
    anchor = suggester.anchor_mgr.resolve_anchor()

    clip_item = ClipboardItem(
        original_length=40,
        sanitized_text='{"api_enabled": true}',
        classification=ClassifiedClipboardPayload(
            content_type=ClipboardContentType.JSON_DATA,
            sub_type="json_object",
            char_count=21,
            line_count=1,
        )
    )

    proposals = suggester.generate_proposals(anchor=anchor, clipboard_item=clip_item)
    assert len(proposals) >= 1
    p_json = proposals[0]
    assert "JSON" in p_json.title
    assert p_json.target_hwnd == 3003


def test_target_window_focus_guard():
    """Verify Focus Guard detects focus divergence and protects misdirected actions."""
    tracker = WindowFocusTracker()
    tracker.set_simulated_window(WindowContext(
        hwnd=4004,
        title="Discord",
        process_name="Discord.exe",
        pid=8888,
        bounding_rect=BoundingRect(left=0, top=0, right=1920, bottom=1080),
    ))
    suggester = ContextualActionSuggester(tracker=tracker)

    # 1. Matching focus should pass
    ok, msg = suggester.validate_target_focus(target_hwnd=4004, expected_process="Discord.exe")
    assert ok is True
    assert "verified" in msg.lower()

    # 2. Divergent HWND should fail
    fail_hwnd, msg_hwnd = suggester.validate_target_focus(target_hwnd=1001, expected_process="Discord.exe")
    assert fail_hwnd is False
    assert "Focus divergence" in msg_hwnd

    # 3. Divergent process name should fail
    fail_proc, msg_proc = suggester.validate_target_focus(target_hwnd=4004, expected_process="Code.exe")
    assert fail_proc is False
    assert "Process divergence" in msg_proc


def test_registered_contextual_anchor_tools():
    """Verify registered contextual anchor tools execute cleanly."""
    # 1. Resolve anchor
    res_anchor = resolve_active_context_anchor(
        window_title="main.py - Phenom - Visual Studio Code",
        process_name="Code.exe"
    )
    assert res_anchor["app_category"] == "IDE"
    assert res_anchor["active_file"] == "main.py"

    # 2. Generate proposals
    res_props = generate_contextual_action_proposals(
        event_type="BUILD_FAILED",
        active_file="services/backend/main.py"
    )
    assert "count" in res_props
    assert "proposals" in res_props

    # 3. Validate focus tool
    res_focus = validate_target_window_focus(
        target_hwnd=0,
        expected_process=""
    )
    assert "is_valid" in res_focus
