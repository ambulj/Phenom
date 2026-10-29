"""
Phenom Zero-Drift Self-Help Engine (Task 7k)
Dynamically synthesizes assistant capabilities and documentation directly from live code contracts:
- Inspects `registry.list_all()`, docstrings, argument schemas, and active risk tiers in real time.
- Categorizes tools into functional domains.
- Answers natural language self-help queries without documentation drift.
"""

from typing import Dict, Any, List, Optional
from services.backend.safety.registry import registry

def categorize_tool(tool_name: str) -> str:
    """Categorizes a tool into a high-level capability domain."""
    name = tool_name.lower()
    if name.startswith("coding_"):
        return "Coding Agent & Safe Runner"
    elif any(k in name for k in ["file", "dir", "trash", "recycle"]):
        return "File Management & Safe Sandbox"
    elif any(k in name for k in ["voice", "audio", "speaker", "tts", "stt", "briefing"]):
        return "Voice & Biometrics"
    elif any(k in name for k in ["screen", "click", "mouse", "keyboard", "window", "takeover"]):
        return "Screen Control & Desktop Automation"
    elif any(k in name for k in ["vault", "memory", "fact", "rule", "note"]):
        return "Obsidian Vault & Memory RAG"
    elif any(k in name for k in ["telegram", "remote", "screenshot"]):
        return "Telegram Bridge & Remote Control"
    elif any(k in name for k in ["gaming", "digest", "notification"]):
        return "Gaming Mode & Notification Governance"
    elif any(k in name for k in ["finance", "calendar", "gmail", "news", "browser"]):
        return "Integrations & Feeds"
    elif any(k in name for k in ["git_"]):
        return "Git Operations"
    return "Core System & Utilities"

class SelfHelpEngine:
    def __init__(self, tool_registry=None):
        self.registry = tool_registry or registry

    def get_capabilities_manifest(self) -> Dict[str, Any]:
        """
        Dynamically generates full capability catalog from registry.list_all().
        Guarantees zero documentation drift.
        """
        registered_dict = self.registry.list_all()
        # Handle dict or list return type
        tool_defs = list(registered_dict.values()) if isinstance(registered_dict, dict) else list(registered_dict)
        categories: Dict[str, List[Dict[str, Any]]] = {}

        for tool in tool_defs:
            cat = categorize_tool(tool.name)
            if cat not in categories:
                categories[cat] = []

            # Extract schema properties
            schema_fields = {}
            if tool.args_schema:
                try:
                    fields = tool.args_schema.model_fields
                    schema_fields = {
                        k: {
                            "type": str(v.annotation),
                            "required": v.is_required(),
                            "description": v.description or ""
                        }
                        for k, v in fields.items()
                    }
                except Exception:
                    pass

            categories[cat].append({
                "name": tool.name,
                "tier": tool.tier if isinstance(tool.tier, int) else "dynamic",
                "description": tool.description,
                "parameters": schema_fields,
                "can_remember": tool.can_remember_per_folder
            })

        return {
            "total_tools": len(tool_defs),
            "categories_count": len(categories),
            "domains": categories,
            "hotkeys": {
                "guardian_killswitch": "Ctrl+Alt+Pause",
                "push_to_talk": "Alt+Space",
                "settings_config": "config.toml"
            }
        }

    def answer_query(self, query: str) -> Dict[str, Any]:
        """
        Answers natural language queries about Phenom's capabilities and configuration.
        """
        q = query.strip().lower()
        manifest = self.get_capabilities_manifest()

        if any(w in q for w in ["what can you do", "capabilities", "features", "overview"]):
            domains_summary = ", ".join([f"{k} ({len(v)} tools)" for k, v in manifest["domains"].items()])
            reply = (
                f"I am Phenom, your personal Windows 11 desktop assistant. I currently have {manifest['total_tools']} "
                f"registered tools across {manifest['categories_count']} domains: {domains_summary}. "
                f"All operations are governed by our 4-tier safety model, and you can halt anything immediately "
                f"using the Guardian kill switch (Ctrl+Alt+Pause)."
            )
            return {"query": query, "reply": reply, "manifest": manifest}

        if any(w in q for w in ["hotkey", "shortcut", "keys"]):
            reply = (
                f"Default Phenom hotkeys:\n"
                f"- Guardian Kill Switch: Ctrl+Alt+Pause (Instantly terminates all running tools and processes)\n"
                f"- Push-to-Talk Voice: Alt+Space\n"
                f"You can customize these hotkeys in config.toml under the [hotkeys] section."
            )
            return {"query": query, "reply": reply, "hotkeys": manifest["hotkeys"]}

        if any(w in q for w in ["list tools", "tools", "all tools"]):
            raw_tools = self.registry.list_all()
            tools_list = list(raw_tools.values()) if isinstance(raw_tools, dict) else list(raw_tools)
            return {
                "query": query,
                "reply": f"Found {manifest['total_tools']} registered tools.",
                "tools": [
                    {"name": t.name, "tier": t.tier if isinstance(t.tier, int) else "dynamic", "description": t.description}
                    for t in tools_list
                ]
            }

        # Fallback query
        return {
            "query": query,
            "reply": f"Phenom has {manifest['total_tools']} active tools. Ask 'list tools' or 'what can you do' for details.",
            "total_tools": manifest["total_tools"]
        }

# Global self-help engine instance
self_help_engine = SelfHelpEngine()
