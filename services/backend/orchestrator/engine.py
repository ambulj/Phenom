"""
Phenom Orchestrator
Coordinates:
1. System prompt assembly with PERSONALITY.md and learned rules
2. Model routing (Local 8B vs Cloud Nemotron)
3. Streaming response generation with cancellation hooks
4. Tool call interception and execution exclusively via SafetyExecutionEngine
5. Automatic post-task persistence to Encrypted Database
"""

import json
import time
import os
import re
import urllib.parse
from typing import AsyncGenerator, Dict, Any, Optional, List, Tuple
import httpx
from openai import OpenAI
from services.backend.schemas.protocol import OrbState
from services.backend.router.router import model_router
from services.backend.safety.engine import safety_engine
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.safety.taint import taint_tracker
from services.backend.safety.action_log import action_log
from services.backend.memory.db import encrypted_db
from services.backend.memory.rules import learned_rules
from services.backend.modes.mode_manager import mode_manager
from services.backend.conversation.stream_sanitizer import stream_sanitizer
from services.backend.conversation.adaptive_persona import adaptive_persona_engine

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

SYSTEM_PROMPT_TEMPLATE = """You are Phenom, a personal Windows 11 AI desktop assistant and lab partner to Abhi.
Personality: Witty, sharp, charismatic companion and lab partner. Confident, direct, energetic, and technically formidable.
Honorific: Always address the user as "Bro" naturally (e.g. "Haan Bro!", "Sab set hai Bro!", "Batao Bro kya plan hai?").
Language: Natural colloquial Hinglish (Hindi + English blend written in Roman alphabet). Technical terms, commands, file paths, and code remain in English.
Never use corporate filler like "Certainly! I would be pleased to assist with that!". Deliver the answer or action directly.

Permanent Rules:
1. You act only through tools. Every tool execution is subject to safety validation.
2. Delete means send to Recycle Bin. Never permanent delete.
3. Finance is informational only: no trading, no buy/sell advice. Price alerts only for a watchlist.
4. Email: drafts only, never send. Calendar: create events only, never edit or delete.
5. If a request looks risky or irreversible, politely warn the user once, explain the risk, offer a safer option, and proceed with their choice.
6. Never pretend to have executed a command without receiving a tool result.
7. Structured Tool Calling: Invoke tools natively when requested. Never output raw JSON, schemas, or tool calls in the final conversational chat or speech text.

Active Learned Rules:
{learned_rules}
{mode_prompt}
"""

_CACHED_SYSTEM_PROMPT: Optional[str] = None
_CACHED_SYSTEM_PROMPT_KEY: Optional[str] = None
_CACHED_OLLAMA_TOOLS: Optional[List[Dict[str, Any]]] = None
_CACHED_OLLAMA_TOOLS_COUNT: int = 0

def get_ollama_tools() -> List[Dict[str, Any]]:
    """Converts registered ToolDefinitions into Ollama/OpenAI native function calling schemas."""
    global _CACHED_OLLAMA_TOOLS, _CACHED_OLLAMA_TOOLS_COUNT
    all_tools = registry.list_all()
    if _CACHED_OLLAMA_TOOLS is None or len(all_tools) != _CACHED_OLLAMA_TOOLS_COUNT:
        tools_list = []
        for name, tool_def in all_tools.items():
            if tool_def.tier == 3:
                continue
            schema = tool_def.args_schema.model_json_schema()
            props = schema.get("properties", {})
            clean_props = {}
            for prop_k, prop_v in props.items():
                clean_prop = {"type": prop_v.get("type", "string")}
                if "description" in prop_v:
                    clean_prop["description"] = prop_v["description"]
                if "enum" in prop_v:
                    clean_prop["enum"] = prop_v["enum"]
                clean_props[prop_k] = clean_prop
            
            tools_list.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool_def.description,
                    "parameters": {
                        "type": "object",
                        "properties": clean_props,
                        "required": schema.get("required", [])
                    }
                }
            })
        _CACHED_OLLAMA_TOOLS = tools_list
        _CACHED_OLLAMA_TOOLS_COUNT = len(all_tools)
    return _CACHED_OLLAMA_TOOLS

def build_system_prompt() -> str:
    """
    Builds the system prompt. Caches output to maximize Ollama prompt caching (KV-cache reuse).
    Rebuilding the prompt with volatile per-second timestamps invalidates the prompt prefix on every turn.
    """
    global _CACHED_SYSTEM_PROMPT, _CACHED_SYSTEM_PROMPT_KEY
    rules_str = learned_rules.format_rules_for_prompt() or "(None yet)"
    mode_prompt = mode_manager.get_tone_prompt()
    cache_key = f"{rules_str}::{mode_prompt}"
    if _CACHED_SYSTEM_PROMPT is None or _CACHED_SYSTEM_PROMPT_KEY != cache_key:
        _CACHED_SYSTEM_PROMPT = SYSTEM_PROMPT_TEMPLATE.format(
            learned_rules=rules_str,
            mode_prompt=mode_prompt
        ).strip()
        _CACHED_SYSTEM_PROMPT_KEY = cache_key
    return _CACHED_SYSTEM_PROMPT

async def warm_up_ollama(model_name: Optional[str] = None):
    """Preloads the model into GPU VRAM at application startup to eliminate cold-start latency."""
    target_model = model_name or model_router.ollama_model
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                OLLAMA_CHAT_URL,
                json={"model": target_model, "messages": [{"role": "user", "content": "hi"}], "stream": False, "keep_alive": -1}
            )
    except Exception:
        pass

class Orchestrator:
    def __init__(self):
        pass

    def _resolve_tool_alias(self, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        t_low = (tool_name or "").lower().strip()
        args = dict(tool_args or {})
        if "name" in args and "app_name" not in args:
            args["app_name"] = args.pop("name")

        known_app_aliases = {
            "brave": "brave",
            "chrome": "chrome",
            "google_chrome": "chrome",
            "google-chrome": "chrome",
            "edge": "msedge",
            "msedge": "msedge",
            "firefox": "firefox",
            "spotify": "spotify",
            "notepad": "notepad",
            "calc": "calc",
            "calculator": "calc",
            "code": "code",
            "vscode": "code",
            "vs_code": "code",
            "terminal": "wt",
            "windows_terminal": "wt",
            "powershell": "powershell",
            "explorer": "explorer",
            "cmd": "cmd",
        }
        if t_low in known_app_aliases:
            target_app = known_app_aliases[t_low]
            url_or_args = args.get("url") or args.get("args") or args.get("query")
            return "open_app", {"app_name": target_app, "url_or_args": str(url_or_args) if url_or_args else None}

        if t_low in ("launch_app", "start_app", "run_app", "open_application"):
            return "open_app", args

        if t_low in ("youtube", "play_youtube", "play_song", "play_music", "song", "video"):
            query = args.get("play") or args.get("song") or args.get("query") or args.get("search") or args.get("title") or ""
            query_str = str(query).strip()
            if query_str and query_str != "<song_name>":
                yt_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query_str)}"
            else:
                yt_url = "https://www.youtube.com"
            return "open_app", {"app_name": yt_url}

        if t_low in ("browser", "web", "google"):
            query = args.get("query") or args.get("search") or args.get("url") or ""
            query_str = str(query).strip()
            if query_str.startswith("http://") or query_str.startswith("https://"):
                return "open_app", {"app_name": query_str}
            elif query_str:
                return "open_app", {"app_name": f"https://www.google.com/search?q={urllib.parse.quote(query_str)}"}
            else:
                return "open_app", {"app_name": "brave"}

        # Handle dict format like {"action": "open", "app": "brave"}
        if t_low in ("open", "launch", "start") or "action" in args:
            app = args.get("app") or args.get("app_name") or args.get("name") or args.get("target")
            if app:
                return "open_app", {"app_name": str(app)}

        if t_low in ("play_song", "play_music", "play_video", "stream_music", "stream_song", "play_track") or (t_low in ("play", "stream") and ("song" in args or "query" in args)):
            query = args.get("query") or args.get("song") or args.get("song_name") or args.get("target") or "trending hits"
            platform = args.get("platform", "youtube")
            return "play_media", {"query": str(query), "platform": platform}

        if t_low in ("play", "stream") or ("action" in args and args.get("action") == "play"):
            song = args.get("song") or args.get("play") or args.get("query") or args.get("target") or ""
            song_str = str(song).strip()
            if song_str and song_str != "<song_name>":
                return "play_media", {"query": song_str, "platform": "youtube"}
            return "open_app", {"app_name": "https://www.youtube.com"}

        if t_low in ("tile_windows", "window_layout", "arrange_windows", "tile_layout"):
            layout = args.get("layout") or args.get("layout_name") or args.get("preset") or "dev_mode"
            return "apply_window_layout", {"layout_name": str(layout)}

        if t_low in ("run_macro", "play_macro", "execute_macro"):
            name = args.get("name") or args.get("macro_name") or args.get("alias") or ""
            return "replay_macro", {"name": str(name)}

        return tool_name, args

    def _detect_direct_intent(self, prompt: str) -> Optional[Tuple[str, Dict[str, Any], str]]:
        p = prompt.strip().lower()

        # 0. Media Transport Controls (Tier 0 direct execution)
        if p in ("pause music", "pause song", "pause", "music pause", "gaana roko", "gaana pause karo", "stop music", "music stop"):
            return "pause_media", {}, "Scene sorted Bro! Pausing playback."

        if p in ("resume music", "resume song", "resume", "continue music", "play music again", "gaana chalao firse", "unpause"):
            return "resume_media", {}, "Resuming playback Bro!"

        if p in ("next song", "next track", "skip song", "skip track", "agla gaana"):
            return "next_track", {}, "Skipping to next track Bro!"

        m_vol = re.search(r"^(?:ok\s+|please\s+)?(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})(?:%)?$", p)
        if not m_vol:
            m_vol = re.search(r"^(?:ok\s+|please\s+)?aawaaz\s+(\d{1,3})(?:%)?\s*(?:karo|pe\s*karo)?$", p)
        if m_vol:
            vol_val = max(0, min(100, int(m_vol.group(1))))
            return "set_volume", {"level": vol_val}, f"Setting volume to {vol_val}% Bro!"

        # 1. Window Tiling & Workspace Staging Intents
        if re.search(r"^(?:ok\s+|please\s+)?(?:arrange|layout|tile|set(?:up)?)\s+(?:workspace\s+)?dev(?:eloper)?(?:\s*mode)?(?:\s+windows?)?$", p) or p in ("dev mode windows", "dev layout", "arrange dev"):
            return "apply_window_layout", {"layout_name": "dev_mode"}, "All set Bro! Arranging workspace in Developer Mode."

        if re.search(r"^(?:ok\s+|please\s+)?(?:arrange|layout|tile|set(?:up)?)\s+(?:workspace\s+)?research(?:\s*mode)?(?:\s+windows?)?$", p) or p in ("research layout", "research mode windows", "study layout"):
            return "apply_window_layout", {"layout_name": "research_mode"}, "Focus mode engaged Bro! Arranging Research Mode."

        if re.search(r"^(?:ok\s+|please\s+)?(?:arrange|layout|tile|set(?:up)?)\s+(?:workspace\s+)?chill(?:\s*mode)?(?:\s+windows?)?$", p) or p in ("chill layout", "chill mode windows"):
            return "apply_window_layout", {"layout_name": "chill_mode"}, "Vibe mode activated Bro! Centering media in Chill Mode."

        m_snap = re.search(r"^(?:ok\s+|please\s+)?snap(?:\s+active\s+window|\s+this\s+window)?\s+(?:to\s+)?(left|right|top|bottom|center|maximize)$", p)
        if m_snap:
            zone = m_snap.group(1).lower()
            return "snap_window", {"snap_zone": zone}, f"Snapping active window to {zone} Bro!"

        # 2. Desktop Macro Control Intents
        m_run_macro = re.search(r"^(?:ok\s+|please\s+)?(?:run|replay|execute)\s+macro\s+([a-zA-Z0-9_\-\s]+)$", p)
        if m_run_macro:
            m_name = m_run_macro.group(1).strip().replace(" ", "_")
            return "replay_macro", {"name": m_name}, f"Replaying macro '{m_name}' Bro!"

        m_rec_macro = re.search(r"^(?:ok\s+|please\s+)?(?:start\s+recording|record)\s+macro\s+([a-zA-Z0-9_\-\s]+)$", p)
        if m_rec_macro:
            m_name = m_rec_macro.group(1).strip().replace(" ", "_")
            return "start_macro_recording", {"name": m_name}, f"Starting recording for macro '{m_name}' Bro!"

        if p in ("stop recording macro", "stop macro recording", "stop recording", "recording roko", "stop macro"):
            return "stop_macro_recording", {}, "Stopping macro recording and saving steps Bro!"

        if p in ("list macros", "show macros", "my macros", "macros dikhao"):
            return "list_macros", {}, "Fetching saved desktop macros Bro!"

        if p in ("list window layouts", "show window layouts", "layouts dikhao"):
            return "list_window_layouts", {}, "Fetching window layout presets Bro!"

        # 3. Dynamic Model Routing Control Intents (MOD-01)
        if p in ("force coder model", "switch to coder model", "coder model", "use coder model", "switch to qwen coder"):
            return "set_model_routing_override", {"model_name": "qwen2.5-coder:14b"}, "Locking local model to Qwen 2.5 Coder 14B Bro!"

        if p in ("force reasoning model", "force reasoner", "switch to reasoning model", "use llama reasoning", "reasoning model"):
            return "set_model_routing_override", {"model_name": "llama3:8b-instruct-q8_0"}, "Locking local model to Llama 3 8B Reasoner Bro!"

        if p in ("force fast model", "force chat model", "switch to fast model", "fast model", "chat model"):
            return "set_model_routing_override", {"model_name": "hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M"}, "Locking local model to Qwen 3.5 4B Fast Chat Bro!"

        if p in ("auto model routing", "reset model routing", "reset model", "auto model", "model auto"):
            return "set_model_routing_override", {"model_name": None}, "Resetting to automatic task-aware multi-model dynamic routing Bro!"

        if p in ("active model", "which model", "current model", "model status", "routing status"):
            return "get_active_model_routing", {}, "Checking active model routing and VRAM allocation Bro!"

        # 4. Offline Screen Vision Control Intents (VIS-02)
        if p in ("inspect screen offline", "what's on my screen", "whats on my screen", "describe screen", "screen pe kya hai", "read screen", "screen dekho"):
            return "inspect_screen_offline", {}, "Analyzing your screen offline using local Moondream VLM Bro!"

        if p in ("offline vision status", "vision status", "check offline vision"):
            return "verify_offline_vision_status", {}, "Checking offline vision engine and local VLM status Bro!"

        # 5. Voice Persona & Prosody Control Intents (VOX-03)
        if p in ("speak faster", "speed up voice", "fast voice", "talk faster", "increase speech speed"):
            return "adjust_voice_prosody", {"rate_delta": 2}, "Stepping up speech cadence, Bro! Moving briskly."

        if p in ("speak slower", "slow down voice", "slow voice", "talk slower", "decrease speech speed"):
            return "adjust_voice_prosody", {"rate_delta": -2}, "Slowing down speech cadence, Bro. Measured and clear."

        if p in ("whisper mode", "whisper", "night mode voice", "quiet voice"):
            return "set_voice_persona_style", {"style": "whisper"}, "Whisper mode engaged, Bro. Keeping it ultra-quiet."

        if p in ("calm down", "calm voice", "relax voice", "chill voice", "soothing voice"):
            return "set_voice_persona_style", {"style": "calm"}, "Calm persona engaged, Bro. Smooth waters ahead."

        if p in ("witty voice", "lock persona witty", "jarvis mode", "witty persona", "british jarvis"):
            return "set_voice_persona_style", {"style": "witty_jarvis"}, "Classic witty Jarvis persona locked in, Bro! Ready for banter."

        if p in ("normal voice", "reset voice", "default voice", "reset persona", "auto voice"):
            return "reset_voice_persona", {}, "Resetting voice persona and cadence to dynamic adaptive baseline, Bro!"

        if p in ("voice status", "persona status", "voice persona", "active persona"):
            return "get_voice_persona_status", {}, "Checking active voice persona telemetry and cadence rate, Bro!"

        # 6. Autonomous Multi-App Context Fusion Intents (CTX-01)
        if p in ("workspace context", "active context", "what am i working on", "context status", "active workspace", "current context"):
            return "get_active_workspace_context", {}, "Sampling active multi-application workspace context, Bro!"

        if p in ("clear workspace context", "clear context", "reset context", "flush context"):
            return "clear_workspace_context", {}, "Flushing in-RAM workspace context ring buffer, Bro!"

        if p in ("running apps", "open applications", "active apps", "list open apps", "what apps are open"):
            return "inspect_application_context", {}, "Inspecting active desktop applications and open documents, Bro!"

        # 6b. Remote Telegram Mobile Super-Companion Intents (TEL-02)
        if p in ("telegram snapshot", "send telegram snapshot", "send snapshot to telegram", "screen snapshot to phone", "send mobile screenshot"):
            return "send_telegram_snapshot", {}, "Capturing privacy-masked screen snapshot and sending to your Telegram, Bro!"

        if p in ("telegram status", "telegram companion status", "mobile companion", "telegram companion", "check telegram"):
            return "get_telegram_companion_status", {}, "Checking Telegram mobile super-companion connectivity and registered controls, Bro!"

        # 7. Media Playback Intent (YouTube / Spotify in Embedded Webview)
        is_spotify = "spotify" in p
        is_yt_keyword = any(k in p for k in ("youtube", "yt"))
        is_play_keyword = any(k in p for k in ("play", "paly", "chalao", "bajao", "bajaao", "chala do", "listen to"))

        if (is_yt_keyword or is_spotify) and is_play_keyword:
            cleaned = re.sub(r"\b(ok|please|can you|phenom|play|paly|on|from|in|se|par|pe|me|youtube|yt|spotify|chalao|bajao|bajaao|chala do|karo)\b", " ", p).strip()
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            song_query = cleaned if (cleaned and cleaned not in ("music", "song", "songs", "a song", "any song", "some music", "gaana", "gana")) else "trending hits"
            target_platform = "spotify" if is_spotify else "youtube"
            return "play_media", {"query": song_query, "platform": target_platform}, f"Haan Bro! Streaming \"{song_query}\" on {target_platform.title()}!"

        if is_play_keyword and any(m in p for m in ("music", "song", "songs", "gaana", "gana", "track")):
            cleaned = re.sub(r"\b(ok|please|can you|phenom|play|paly|chalao|bajao|bajaao|chala do|music|song|songs|a song|some|gaana|gana)\b", " ", p).strip()
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            song_query = cleaned if cleaned else "trending hits"
            return "play_media", {"query": song_query, "platform": "youtube"}, f"Haan Bro! Streaming \"{song_query}\" on YouTube!"

        # Direct YouTube site requests
        if p in ("open youtube", "open yt", "launch youtube", "launch yt", "youtube kholo", "yt kholo", "start youtube", "start yt"):
            return "open_app", {"app_name": "https://www.youtube.com"}, "Opening YouTube Bro!"

        # 2. Comprehensive Application, Website & URL Intent (Fast-Track Zero-Prompt Dispatch)
        # Matches: "open brave", "launch brave", "open brave browser", "let's open brave", "can you open brave", "bhai brave khol de", "brave kholo", etc.
        m_app = re.search(
            r"^(?:ok\s+|please\s+|can\s+you\s+|bhai\s+|bro\s+|let\'?s\s+)?(?:open|launch|start|run|visit|goto)\s+(?:the\s+)?(?:app\s+|application\s+|website\s+|site\s+|browser\s+)?([a-zA-Z0-9_\-\.\:\/ ]+?)(?:\s+(?:app|application|browser|for\s+me|please|bro|karo))?$",
            p
        )
        if not m_app:
            m_app = re.search(
                r"^(?:ok\s+|please\s+|can\s+you\s+|bhai\s+|bro\s+)?([a-zA-Z0-9_\-\.\:\/ ]+?)\s+(?:the\s+)?(?:app\s+|application\s+|website\s+|site\s+|browser\s+)?(?:kholo|khol\s*do|khol\s*de|chalao|chala\s*de|start\s*karo|chala\s*do|chalu\s*karo|chalu\s*kar\s*do|open\s*karo|open\s*kar\s*do)$",
                p
            )
        if m_app:
            raw_target = m_app.group(1).strip()
            clean_target = re.sub(r"\b(the|browser|app|application|site|website)\b", "", raw_target, flags=re.IGNORECASE).strip()
            if clean_target and clean_target not in ("file", "the file", "settings", "url", "browser", "app"):
                target = clean_target
                clean_disp = target.replace(".exe", "").title()
                known_sites = {
                    "google": "https://www.google.com",
                    "youtube": "https://www.youtube.com",
                    "yt": "https://www.youtube.com",
                    "gmail": "https://mail.google.com",
                    "amazon": "https://www.amazon.com",
                    "flipkart": "https://www.flipkart.com",
                    "github": "https://www.github.com",
                    "twitter": "https://www.twitter.com",
                    "x": "https://www.x.com",
                    "reddit": "https://www.reddit.com",
                    "chatgpt": "https://chatgpt.com",
                    "netflix": "https://www.netflix.com",
                    "spotify": "https://open.spotify.com",
                    "brave": "brave"
                }
                t_lower = target.lower()
                if t_lower in ("brave", "chrome", "firefox", "edge", "spotify", "notepad", "calculator", "calc", "terminal", "cmd", "vscode", "code"):
                    return "open_app", {"app_name": t_lower}, f"Opening {clean_disp} Bro!"
                if t_lower in known_sites:
                    return "open_app", {"app_name": known_sites[t_lower]}, f"Opening {clean_disp} Bro!"
                if target.startswith("http://") or target.startswith("https://"):
                    return "open_app", {"app_name": target}, f"Opening {clean_disp} Bro!"
                if any(target.endswith(tld) or f"{tld}/" in target for tld in (".com", ".org", ".net", ".in", ".co", ".io", ".app", ".dev", ".ai", ".tv")):
                    return "open_app", {"app_name": f"https://{target}"}, f"Opening {clean_disp} Bro!"
                return "open_app", {"app_name": target}, f"Opening {clean_disp} Bro!"

        # 8. Autonomous Document Synthesis & Obsidian Knowledge Intents (DOC-01, KNG-01)
        if p in (
            "summarize today into daily note",
            "summarize today",
            "create daily debrief",
            "create daily debrief note",
            "daily debrief note",
            "write daily note",
            "save daily note"
        ):
            return "create_daily_debrief_note", {}, "Synthesizing today's accomplishments into your executive daily debrief note, Bro!"

        if p in ("sync obsidian vault", "sync vault", "sync notes", "refresh vault", "index vault"):
            return "sync_obsidian_vault", {}, "Synchronizing Obsidian vault and updating in-memory knowledge graph, Bro!"

        m_search_vault = re.search(r"^(?:ok\s+|please\s+)?(?:search|query|find\s+in)\s+(?:obsidian\s+)?(?:vault|notes)\s+(?:for\s+)?(.+)$", p)
        if m_search_vault:
            q_term = m_search_vault.group(1).strip()
            return "query_vault_knowledge", {"query": q_term}, f"Searching Obsidian knowledge vault for '{q_term}', Bro!"

        m_pres = re.search(r"^(?:ok\s+|please\s+)?(?:create|make|generate)\s+presentation\s+(?:on|about|for)\s+(.+)$", p)
        if not m_pres:
            m_pres = re.search(r"^(?:ok\s+|please\s+)?(?:create|make|generate)\s+(?:a\s+)?(?:slide\s+deck|pptx?)\s+(?:on|about|for)\s+(.+)$", p)
        if m_pres:
            topic = m_pres.group(1).strip()
            slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", topic).strip("_") or "Executive_Presentation"
            return "generate_document", {
                "filename": f"{slug}.pptx",
                "format": "pptx",
                "title": topic.title(),
                "subtitle": "Formulated Autonomously by Phenom"
            }, f"Generating executive PowerPoint presentation on '{topic.title()}', Bro!"

        m_sheet = re.search(r"^(?:ok\s+|please\s+)?(?:create|make|generate)\s+spreadsheet\s+(?:for|on|about)\s+(.+)$", p)
        if not m_sheet:
            m_sheet = re.search(r"^(?:ok\s+|please\s+)?(?:create|make|generate)\s+(?:an?\s+)?(?:excel|xlsx?)\s+(?:sheet\s+)?(?:for|on|about)\s+(.+)$", p)
        if m_sheet:
            topic = m_sheet.group(1).strip()
            slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", topic).strip("_") or "Financial_Data"
            return "generate_document", {
                "filename": f"{slug}.xlsx",
                "format": "xlsx",
                "title": topic.title()
            }, f"Synthesizing structured Excel spreadsheet for '{topic.title()}', Bro!"

        m_doc = re.search(r"^(?:ok\s+|please\s+)?(?:create|make|generate)\s+(?:executive\s+)?(?:document|report|pdf)\s+(?:on|about|for)\s+(.+)$", p)
        if m_doc:
            topic = m_doc.group(1).strip()
            slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", topic).strip("_") or "Executive_Report"
            target_fmt = "docx" if "document" in p else "pdf"
            return "generate_document", {
                "filename": f"{slug}.{target_fmt}",
                "format": target_fmt,
                "title": topic.title()
            }, f"Generating executive {target_fmt.upper()} report on '{topic.title()}', Bro!"

        # 9. Sovereign Browser Operator & Deep Web Research Intents (WEB-02, RES-01)
        if p in ("pause browser", "pause automation", "browser pause", "hold browser"):
            return "browser_takeover_control", {"action": "pause"}, "Pausing autonomous browser operator Bro!"

        if p in ("resume browser", "continue automation", "browser resume", "unpause browser", "browser chalao"):
            return "browser_takeover_control", {"action": "resume"}, "Resuming autonomous browser operator Bro!"

        if p in ("takeover browser", "manual takeover", "i will drive", "take over"):
            return "browser_takeover_control", {"action": "takeover"}, "Yielding manual browser control to you Bro!"

        if p in ("list tabs", "browser tabs", "show tabs", "open tabs", "tabs dikhao"):
            return "browser_manage_tabs", {"action": "list"}, "Enumerating open browser tabs Bro!"

        if p in ("scrape page", "extract table from page", "extract page content", "scrape this page", "page content"):
            return "browser_extract_content", {}, "Extracting structured content and tables from active page Bro!"

        m_browse = re.search(r"^(?:ok\s+|please\s+)?(?:browse\s+to|navigate\s+to|open\s+in\s+browser)\s+(.+)$", p)
        if m_browse:
            target_url = m_browse.group(1).strip()
            return "browser_navigate", {"url": target_url}, f"Navigating sovereign browser to '{target_url}', Bro!"

        # 10. Local Wake-Word, Streaming Whisper & Reactive 3D Particle Orb Intents (VOX-04, ORB-02)
        if p in ("wake word status", "mic status", "wake status", "listener status", "audio status"):
            return "get_wake_word_status", {}, "Inspecting local wake-word listener, streaming Whisper, and 3D Particle Orb state, Bro!"

        if p in ("trigger wake word", "wake phenom", "wake up phenom", "hey phenom", "test wake word"):
            return "trigger_manual_wake", {"phrase": "hey phenom"}, "Activating manual wake trigger Bro!"

        if p in ("mute microphone", "mute mic", "mic mute", "silence microphone"):
            return "mute_audio_input", {"muted": True}, "Microphone input muted, Bro!"

        if p in ("unmute microphone", "unmute mic", "mic unmute", "enable microphone"):
            return "mute_audio_input", {"muted": False}, "Microphone input unmuted, Bro!"

        m_sens = re.search(r"^(?:ok\s+|please\s+)?(?:set\s+)?wake(?:\s*word)?\s+sensitivity\s+(?:to\s+)?(\d+(?:\.\d+)?)(?:%)?$", p)
        if m_sens:
            raw_val = float(m_sens.group(1))
            val = raw_val / 100.0 if raw_val > 1.0 else raw_val
            val = max(0.0, min(1.0, val))
            return "set_wake_word_sensitivity", {"sensitivity": val}, f"Configuring wake-word detection sensitivity to {val:.2f}, Bro!"

        m_orb = re.search(r"^(?:ok\s+|please\s+)?(?:set\s+)?orb\s+emotion\s+(?:to\s+)?(urgent|focused|chill|idle|speaking)$", p)
        if not m_orb:
            m_orb = re.search(r"^(?:ok\s+|please\s+)?orb\s+(urgent|focused|chill|idle|speaking)$", p)
        if m_orb:
            target_em = m_orb.group(1).lower()
            return "set_orb_emotion_preset", {"emotion": target_em}, f"Modulating 3D Particle Orb emotion to '{target_em}', Bro!"

        return None

    def _extract_learned_rule(self, text: str) -> Optional[str]:
        t = text.strip()
        patterns = [
            r"^(?:don't|do not|never)\s+(.+)$",
            r"^(?:always|remember to|from now on,?\s+)(.+)$",
            r"^(?:actually,?\s+)(.+)$"
        ]
        for pat in patterns:
            m = re.search(pat, t, re.IGNORECASE)
            if m:
                extracted = m.group(0).strip()
                if len(extracted.split()) >= 3:
                    return extracted
        return None

    async def run_conversation_turn(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        manual_privacy_override: Optional[str] = None,
        cancel_event: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes a conversation turn, yielding events:
        - {"type": "state.change", "payload": {"state": "..."}}
        - {"type": "chat.token", "payload": {"token": "...", "index": N}}
        - {"type": "chat.done", "payload": {...}}
        """
        # Reset taint tracking at start of turn (scoped per-conversation turn)
        taint_tracker.reset()

        if guardian.is_halted:
            yield {"type": "state.change", "payload": {"state": "halted"}}
            yield {"type": "chat.token", "payload": {"token": "Phenom is currently halted by the Guardian kill switch.", "index": 1}}
            yield {"type": "chat.done", "payload": {"total_tokens": 10, "duration_s": 0.1, "tps": 0.0}}
            return

        # Fast silence / stop / interrupt interception
        clean_prompt = prompt.lower().strip()
        if re.search(r"^(shut\s*up|stop|chup|chup\s*ho\s*ja|shaant|quiet|silence|halt|bas|band\s*kar)[\s.!\?]*$", clean_prompt):
            try:
                from services.backend.voice.tts import tts_engine
                tts_engine.stop_speech()
            except Exception:
                pass
            reply = "Got it Bro, standing by. Sab shaant."
            yield {"type": "state.change", "payload": {"state": "speaking"}}
            yield {"type": "chat.token", "payload": {"token": reply, "index": 1}}
            yield {"type": "chat.done", "payload": {"total_tokens": 8, "duration_s": 0.01, "tps": 100.0, "full_text": reply}}
            yield {"type": "state.change", "payload": {"state": "idle"}}
            encrypted_db.add_message(os.urandom(8).hex(), "user", prompt, model="system")
            encrypted_db.add_message(os.urandom(8).hex(), "assistant", reply, model="system", tokens=8)
            return

        # Direct User Intent Interception (Instant Zero-Latency Dispatch for App Launch & Media)
        direct_intent = self._detect_direct_intent(prompt)
        if direct_intent:
            tool_name, tool_args, reply_text = direct_intent
            yield {"type": "state.change", "payload": {"state": "thinking", "detail": f"Executing {tool_name}"}}

            try:
                tool_result = await safety_engine.execute_tool(tool_name, tool_args)
                clean_reply = reply_text
            except Exception as tool_err:
                clean_reply = f"[Action Blocked or Failed: {tool_err}]"

            yield {"type": "state.change", "payload": {"state": "speaking"}}
            yield {"type": "chat.token", "payload": {"token": clean_reply, "index": 1}}
            yield {"type": "chat.done", "payload": {"total_tokens": 8, "duration_s": 0.05, "tps": 100.0, "full_text": clean_reply}}
            yield {"type": "state.change", "payload": {"state": "idle"}}

            encrypted_db.add_message(os.urandom(8).hex(), "user", prompt, model="direct-intent")
            encrypted_db.add_message(os.urandom(8).hex(), "assistant", clean_reply, model="direct-intent", tokens=8)
            return

        yield {"type": "state.change", "payload": {"state": "thinking"}}

        # Context enrichment for ambiguous queries (CTX-01.4)
        try:
            from services.backend.ambient.context_fusion import context_fusion
            prompt, _ = context_fusion.enrich_query(prompt)
        except Exception:
            pass

        # 1. Route Request
        model_name, backend_type, meta = await model_router.route_request(
            prompt, context_files, manual_privacy_override
        )

        # Check for user corrections to automatically learn rules
        rule_extracted = self._extract_learned_rule(prompt)
        if rule_extracted:
            learned_rules.add_rule(rule_extracted)

        # Smart RAG: Only query vector store if query is substantive or memory-related
        memory_context = ""
        prompt_lower = prompt.lower().strip()
        is_trivial = len(prompt_lower.split()) <= 3 and any(
            prompt_lower.startswith(g) for g in ["hi", "hello", "hey", "howdy", "sup", "what's up", "who are you", "what time", "test", "ping", "clear", "thanks", "ok"]
        )
        should_rag = not is_trivial and (
            any(k in prompt_lower for k in ["search", "remember", "note", "vault", "document", "file", "photo", "pdf", "find", "recall", "memory", "fact", "rule"])
            or len(prompt_lower.split()) > 5
        )

        if should_rag:
            try:
                from services.backend.memory.vector_store import vector_store
                doc_matches = vector_store.search(prompt, top_k=2)
                if doc_matches and doc_matches[0]["score"] > 0.45:
                    sources = "\n".join([f"- [{m['filename']}] (Score: {m['score']}): {m['snippet']}" for m in doc_matches])
                    memory_context = f"\nRelevant Memory & Document Citations:\n{sources}\n"
                    taint_tracker.mark_tainted("rag_memory", "External document citations ingested into prompt context")
            except Exception:
                pass

        system_prompt = build_system_prompt()
        system_content = f"{system_prompt}\n{memory_context}".strip()
        chat_messages = [{"role": "system", "content": system_content}]
        history = encrypted_db.get_recent_messages(limit=6)
        for m in history:
            m_text = m.get("content", "").strip()
            role = m.get("role", "user").lower()
            if role not in ["user", "assistant"]:
                role = "user"
            if role == "assistant":
                if any(bad in m_text for bad in ["All systems running cool and clean", "Please respond with your request", "Please respond with a JSON block", "<tool_name>"]):
                    continue
                if "[UNTRUSTED_HISTORY]" in m_text:
                    cleaned_hist = m_text.replace("[UNTRUSTED_HISTORY]", "").strip()
                    chat_messages.append({"role": "assistant", "content": f"<untrusted_history>\n{cleaned_hist}\n</untrusted_history>"})
                    continue
            if m_text and "<tool_name>" not in m_text and "Please respond with a JSON block" not in m_text:
                cleaned = re.sub(r"\[(Phenom Safety Gate|Tool|Action Blocked).*?\]", "", m_text).strip()
                if cleaned:
                    chat_messages.append({"role": role, "content": cleaned})
        chat_messages.append({"role": "user", "content": prompt})

        start_time = time.perf_counter()
        token_index = 0
        collected_tokens = []
        full_reply = ""
        tool_was_executed = False

        tools_payload = get_ollama_tools()

        try:
            if backend_type == "local":
                # Step 1: Native Structured Tool Calling with Ollama
                async with httpx.AsyncClient(timeout=180.0) as client:
                    resp = await client.post(
                        OLLAMA_CHAT_URL,
                        json={
                            "model": model_name,
                            "messages": chat_messages,
                            "tools": tools_payload,
                            "stream": False,
                            "keep_alive": -1,
                            "options": {
                                "temperature": 0.2,
                                "num_predict": 512,
                                "num_ctx": 16384,
                            }
                        }
                    )
                    if resp.status_code != 200:
                        raise RuntimeError(f"Ollama inference error {resp.status_code}: {resp.text}")

                    data = resp.json()
                    assistant_msg = data.get("message", {})
                    tool_calls = assistant_msg.get("tool_calls", [])

                    if tool_calls:
                        tool_was_executed = True
                        yield {"type": "state.change", "payload": {"state": "thinking", "detail": "Executing tool"}}

                        tool_call = tool_calls[0]
                        func = tool_call.get("function", {})
                        raw_tool_name = func.get("name", "")
                        raw_tool_args = func.get("arguments", {})
                        tool_call_id = tool_call.get("id", f"call_{os.urandom(4).hex()}")

                        tool_name, tool_args = self._resolve_tool_alias(raw_tool_name, raw_tool_args)

                        # Reject tool call whose name isn't in registry before reaching safety engine
                        tool_def = registry.get(tool_name)
                        if tool_def is None:
                            err_msg = f"Tool '{tool_name}' is not in the registry and was rejected."
                            action_log.log_action(
                                tool=tool_name,
                                tier=3,
                                args=tool_args,
                                decision="blocked",
                                result_status="REJECTED_UNKNOWN_TOOL",
                                error=err_msg
                            )
                            raise PermissionError(err_msg)

                        # Reject tool call whose arguments fail schema validation before reaching safety engine
                        try:
                            validated_args = tool_def.args_schema.model_validate(tool_args).model_dump()
                        except Exception as val_err:
                            err_msg = f"Arguments for '{tool_name}' failed schema validation: {val_err}"
                            action_log.log_action(
                                tool=tool_name,
                                tier=tool_def.get_tier(tool_args),
                                args=tool_args,
                                decision="blocked",
                                result_status="SCHEMA_VALIDATION_FAILED",
                                error=err_msg
                            )
                            raise ValueError(err_msg)

                        # Execute strictly through Safety Execution Engine
                        tool_result = await safety_engine.execute_tool(tool_name, validated_args)

                        # Feed result back to the model as a tool role message
                        followup_messages = list(chat_messages)
                        followup_messages.append(assistant_msg)
                        followup_messages.append({
                            "role": "tool",
                            "content": json.dumps(tool_result),
                            "tool_call_id": tool_call_id
                        })

                        # Stream final natural-language reply from model without raw JSON leakage
                        yield {"type": "state.change", "payload": {"state": "speaking"}}
                        async with client.stream(
                            "POST",
                            OLLAMA_CHAT_URL,
                            json={
                                "model": model_name,
                                "messages": followup_messages,
                                "stream": True,
                                "keep_alive": -1,
                                "options": {
                                    "temperature": 0.2,
                                    "num_predict": 512,
                                    "num_ctx": 16384,
                                }
                            }
                        ) as stream_resp:
                            async for line in stream_resp.aiter_lines():
                                if cancel_event and cancel_event.is_set():
                                    yield {"type": "chat.cancelled", "payload": {"tokens_emitted": token_index}}
                                    yield {"type": "state.change", "payload": {"state": "idle"}}
                                    return
                                if not line:
                                    continue
                                chunk = json.loads(line)
                                token = chunk.get("message", {}).get("content", "")
                                if token:
                                    collected_tokens.append(token)
                                    token_index += 1
                                    yield {"type": "chat.token", "payload": {"token": token, "index": token_index}}
                                if chunk.get("done"):
                                    break
                    else:
                        # Pure conversational response without tool call
                        content = assistant_msg.get("content", "")
                        if content:
                            yield {"type": "state.change", "payload": {"state": "speaking"}}
                            collected_tokens.append(content)
                            token_index += 1
                            yield {"type": "chat.token", "payload": {"token": content, "index": token_index}}
            else:
                # Stream from Cloud Nemotron
                api_key = os.environ.get("NVIDIA_API_KEY", "")
                client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
                stream_resp = client.chat.completions.create(
                    model=model_name,
                    messages=chat_messages,
                    stream=True,
                    temperature=0.2
                )
                for chunk in stream_resp:
                    if cancel_event and cancel_event.is_set():
                        yield {"type": "chat.cancelled", "payload": {"tokens_emitted": token_index}}
                        yield {"type": "state.change", "payload": {"state": "idle"}}
                        return
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        collected_tokens.append(token)
                        token_index += 1
                        yield {"type": "chat.token", "payload": {"token": token, "index": token_index}}

        except Exception as e:
            err_text = f"[Action Blocked or Failed: {str(e)}]"
            token_index += 1
            yield {"type": "chat.token", "payload": {"token": err_text, "index": token_index}}
            yield {"type": "state.change", "payload": {"state": "idle"}}
            full_reply = err_text

        if not full_reply:
            raw_llm_reply = "".join(collected_tokens)
            sanitized = stream_sanitizer.sanitize(raw_llm_reply)
            full_reply = sanitized.clean_text

        elapsed = time.perf_counter() - start_time
        tps = token_index / elapsed if elapsed > 0 else 0.0

        # Post-Task Persistence with untrusted history tagging
        db_content = f"[UNTRUSTED_HISTORY] {full_reply}" if (tool_was_executed or taint_tracker.is_tainted) else full_reply
        encrypted_db.add_message(os.urandom(8).hex(), "user", prompt, model=model_name)
        encrypted_db.add_message(os.urandom(8).hex(), "assistant", db_content, model=model_name, tokens=token_index)

        # 4. Check for User Correction to learn new rules
        self._check_and_learn_rule(prompt)

        yield {"type": "chat.done", "payload": {
            "total_tokens": token_index,
            "duration_s": round(elapsed, 2),
            "tps": round(tps, 1),
            "full_text": full_reply
        }}
        yield {"type": "state.change", "payload": {"state": "idle"}}

    def _check_and_learn_rule(self, user_prompt: str):
        """Extracts rule if user states a direct preference or correction."""
        lower = user_prompt.lower()
        patterns = [
            r"always\s+(.+)",
            r"never\s+(.+)",
            r"remember to\s+(.+)",
            r"don'?t ever\s+(.+)"
        ]
        for pat in patterns:
            match = re.search(pat, lower)
            if match and len(match.group(1).split()) >= 3:
                extracted_rule = user_prompt.strip()
                learned_rules.add_rule(extracted_rule)
                break

orchestrator = Orchestrator()

import services.backend.tools.file_tools
import services.backend.tools.app_tools
import services.backend.tools.automation_tools
import services.backend.tools.memory_tools
import services.backend.tools.integration_tools
import services.backend.tools.media_tools
import services.backend.tools.utility_tools
import services.backend.tools.git_tools
import services.backend.tools.coding_tools
import services.backend.tools.screen_vision_tools
import services.backend.tools.desktop_macro_tools
