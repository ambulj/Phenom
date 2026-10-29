"""
Phenom Smart Developer Clipboard Assistance Tool
Inspects text snippets from clipboard for:
- Stack traces (traceback parsing, exception class, file and line extraction)
- JSON payloads (validation, key extraction, pretty structure)
- Git repository URLs (clone recommendation)
- Regex patterns (syntax validation, named groups)
- Code snippets (heuristics)

Tier 0: Pure analytical read-only utility.
"""

import json
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from services.backend.safety.registry import registry

class SmartClipboardArgs(BaseModel):
    content: str = Field(..., description="Clipboard text snippet to analyze.")

def smart_clipboard_preview(args: Dict[str, Any]) -> str:
    preview_snippet = (args.get("content", "")[:60] + "...").replace("\n", " ")
    return f"Analyze clipboard snippet: '{preview_snippet}'"

def analyze_clipboard_snippet(content: str) -> Dict[str, Any]:
    text = content.strip()
    if not text:
        return {"type": "empty", "summary": "Clipboard is empty."}

    # 1. Stack Trace / Traceback Detection
    if "Traceback (most recent call last):" in text or re.search(r'File\s+["\'].*?["\'],\s+line\s+\d+', text):
        frames = re.findall(r'File\s+["\'](.*?)["\'],\s+line\s+(\d+)(?:,\s+in\s+(.*))?', text)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        last_line = lines[-1] if lines else "Unknown Error"
        
        last_frame = frames[-1] if frames else (None, None, None)
        return {
            "type": "stack_trace",
            "summary": f"Detected error traceback: {last_line}",
            "exception_line": last_line,
            "failing_file": last_frame[0] if last_frame else None,
            "failing_line": int(last_frame[1]) if last_frame and last_frame[1] else None,
            "failing_function": last_frame[2] if last_frame else None,
            "total_frames": len(frames),
            "suggested_action": "propose_patch"
        }

    # 2. Git Repository URL
    git_url_match = re.match(r'^(?:git@|https?://)(?:[\w.@:\/~-]+)(?:\.git|\/)?$', text)
    if git_url_match and ("github.com" in text or "gitlab.com" in text or text.endswith(".git")):
        repo_name = text.rstrip("/").split("/")[-1].replace(".git", "")
        return {
            "type": "git_url",
            "summary": f"Detected Git repository: {repo_name}",
            "repo_url": text,
            "repo_name": repo_name,
            "suggested_action": f"git clone {text}"
        }

    # 3. JSON Payload
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return {
                    "type": "json_object",
                    "summary": f"Valid JSON Object with {len(parsed)} keys",
                    "keys": list(parsed.keys())[:10],
                    "total_keys": len(parsed),
                    "suggested_action": "format_or_inspect"
                }
            elif isinstance(parsed, list):
                return {
                    "type": "json_array",
                    "summary": f"Valid JSON Array with {len(parsed)} items",
                    "item_count": len(parsed),
                    "suggested_action": "format_or_inspect"
                }
        except Exception:
            pass

    # 4. Regex Pattern
    if text.startswith("/") and text.endswith("/") and len(text) > 2:
        regex_candidate = text[1:-1]
        try:
            compiled = re.compile(regex_candidate)
            return {
                "type": "regex",
                "summary": f"Valid Regular Expression pattern: {regex_candidate}",
                "pattern": regex_candidate,
                "group_count": compiled.groups,
                "suggested_action": "test_regex"
            }
        except Exception:
            pass

    # 5. Standard Code Snippet / Text
    line_count = len(text.splitlines())
    return {
        "type": "text_snippet",
        "summary": f"Text snippet ({line_count} lines, {len(text)} characters)",
        "line_count": line_count,
        "char_count": len(text),
        "suggested_action": "copy_or_summarize"
    }

@registry.register(
    name="smart_clipboard_inspect",
    tier=0,
    description="Analyzes clipboard snippets for stack traces, JSON, Git URLs, regex patterns, or code.",
    args_schema=SmartClipboardArgs,
    preview_fn=smart_clipboard_preview,
    can_remember_per_folder=False
)
def handle_smart_clipboard_inspect(content: str) -> Dict[str, Any]:
    return analyze_clipboard_snippet(content)
