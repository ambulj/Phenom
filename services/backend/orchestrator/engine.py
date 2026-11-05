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
from services.backend.memory.db import encrypted_db
from services.backend.memory.rules import learned_rules
from services.backend.modes.mode_manager import mode_manager

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

SYSTEM_PROMPT_TEMPLATE = """You are Phenom, a personal Windows 11 AI desktop assistant and lab partner to Abhi.
Current Date & Time: {current_time}
{mode_prompt}
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

Active Learned Rules:
{learned_rules}

Available Tools:
{tool_descriptions}

Core Instructions:
1. Action Execution: When the user requests ANY action, media control, playback change, volume adjustment, app launch, news briefing, weather, calculation, reminder, or system task:
   - Output ONLY the JSON execution block immediately:
```json
{{"tool": "open_app", "args": {{"app_name": "brave"}}}}
```
   - CRITICAL TOOL INVOCATION RULES:
     * You MUST ONLY use the EXACT registered tool names listed in "Available Tools" above. NEVER invent new tool names (e.g. NEVER emit `{{"tool": "brave"}}` or `{{"tool": "youtube"}}`).
     * To launch ANY desktop application (Brave, Chrome, Spotify, Notepad, Calculator, VS Code) or open any website/video/music (YouTube search, news), ALWAYS call the `open_app` tool!
       Example for "open brave": {{"tool": "open_app", "args": {{"app_name": "brave"}}}}
       Example for "play Baarishein on YouTube": {{"tool": "open_app", "args": {{"app_name": "https://www.youtube.com/results?search_query=Baarishein"}}}}
       Example for "Spotify kholo": {{"tool": "open_app", "args": {{"app_name": "spotify"}}}}
   - Do NOT provide conversational preamble, greetings, or meta-explanations before the tool JSON block. Output the JSON execution block immediately.

2. General Conversation & Interruption:
   - When the user greets you (e.g. "hi", "kya haal hai Bro", "hello") or makes casual conversation, respond in 1-2 natural, punchy Hinglish sentences addressing the user as "Bro". Never mention JSON, tools, or schemas to the user. Never offer canned system status reports unless explicitly asked.
   - If the user says "shut up", "stop", "chup", "quiet", "shaant", never preach, lecture, or apologize like a generic customer service bot. Be crisp and loyal: "Got it Bro, standing by. Sab shaant."

3. Questions & Knowledge: When the user asks a question, explain directly and concisely in natural Hinglish, keeping technical details in crisp English.
"""

_CACHED_TOOLS_STR: Optional[str] = None
_CACHED_TOOLS_LEN: int = 0

def get_cached_tool_descriptions() -> str:
    global _CACHED_TOOLS_STR, _CACHED_TOOLS_LEN
    all_tools = registry.list_all()
    if _CACHED_TOOLS_STR is None or len(all_tools) != _CACHED_TOOLS_LEN:
        tool_lines = []
        for name, tool_def in all_tools.items():
            fields = list(tool_def.args_schema.model_fields.keys())
            tool_lines.append(f"- {name}({', '.join(fields)}): {tool_def.description} [Tier {tool_def.tier}]")
        _CACHED_TOOLS_STR = "\n".join(tool_lines)
        _CACHED_TOOLS_LEN = len(all_tools)
    return _CACHED_TOOLS_STR

def build_system_prompt() -> str:
    tools_str = get_cached_tool_descriptions()
    rules_str = learned_rules.format_rules_for_prompt() or "(None yet)"
    mode_prompt = mode_manager.get_tone_prompt()
    from datetime import datetime
    current_time_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    return SYSTEM_PROMPT_TEMPLATE.format(
        current_time=current_time_str,
        mode_prompt=mode_prompt,
        learned_rules=rules_str,
        tool_descriptions=tools_str
    )

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
            return "open_app", {"app_name": "https://www.youtube.com"}, "Haan Bro! Opening YouTube for you..."

        # 2. Website & URL Intent
        m_web = re.search(r"^(?:ok\s+|please\s+)?(?:open|launch|start|visit|goto)\s+(?:website\s+|site\s+)?([a-zA-Z0-9_\-\.\:\/]+)$", p)
        if not m_web:
            m_web = re.search(r"^(?:ok\s+|please\s+)?([a-zA-Z0-9_\-\.\:\/]+)\s+(?:website\s+|site\s+)?(?:kholo|chalao|khol\s*do|start\s*kar\s*do|open\s*karo)$", p)
        if m_web:
            target = m_web.group(1).strip()
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
                "spotify": "https://open.spotify.com"
            }
            if target.startswith("http://") or target.startswith("https://"):
                return "open_app", {"app_name": target}, f"Haan Bro! Opening {target}..."
            if any(target.endswith(tld) or f"{tld}/" in target for tld in (".com", ".org", ".net", ".in", ".co", ".io", ".app", ".dev", ".ai", ".tv")):
                full_url = f"https://{target}"
                return "open_app", {"app_name": full_url}, f"Haan Bro! Opening {target}..."
            if target in known_sites:
                return "open_app", {"app_name": known_sites[target]}, f"Haan Bro! Opening {target.title()}..."

            # 3. Application Intent
            if target not in ("file", "the file", "settings", "url", "browser", "app"):
                clean_disp = target.replace(".exe", "").title()
                return "open_app", {"app_name": target}, f"Haan Bro! Launching {clean_disp}..."

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
            yield {"type": "chat.done", "payload": {"total_tokens": 8, "duration_s": 0.01, "tps": 100.0}}
            yield {"type": "state.change", "payload": {"state": "idle"}}
            encrypted_db.add_message(os.urandom(8).hex(), "user", prompt, model="system")
            encrypted_db.add_message(os.urandom(8).hex(), "assistant", reply, model="system", tokens=8)
            return

        # Direct User Intent Interception (Instant Zero-Latency Dispatch for App Launch & YouTube)
        direct_intent = self._detect_direct_intent(prompt)
        if direct_intent:
            tool_name, tool_args, reply_text = direct_intent
            yield {"type": "state.change", "payload": {"state": "speaking"}}
            yield {"type": "chat.token", "payload": {"token": reply_text + "\n", "index": 1}}
            yield {"type": "state.change", "payload": {"state": "thinking", "detail": f"Executing {tool_name}"}}
            yield {"type": "chat.token", "payload": {"token": f"[Phenom Safety Gate: Requesting {tool_name}...\n", "index": 2}}

            try:
                tool_result = await safety_engine.execute_tool(tool_name, tool_args)
                res_val = tool_result.get("result")
                if tool_name == "open_app":
                    app_target = str(tool_args.get("app_name", ""))
                    if "youtube" in app_target.lower():
                        res_msg = "Done Bro! Opening YouTube for you. Enjoy the music!"
                    else:
                        clean_disp = app_target.split("\\")[-1].replace(".exe", "").title()
                        res_msg = f"Done Bro! {clean_disp} is now running."
                elif isinstance(res_val, dict) and "message" in res_val:
                    res_msg = res_val["message"]
                else:
                    res_msg = f"Sab set hai Bro! {tool_name} executed."
                yield {"type": "chat.token", "payload": {"token": res_msg + "\n", "index": 3}}
            except Exception as tool_err:
                res_msg = f"\n[Action Blocked or Failed: {tool_err}]"
                yield {"type": "chat.token", "payload": {"token": res_msg, "index": 3}}
            yield {"type": "chat.done", "payload": {"total_tokens": 15, "duration_s": 0.05, "tps": 100.0}}
            yield {"type": "state.change", "payload": {"state": "idle"}}

            full_reply = f"{reply_text}\n{res_msg}"
            encrypted_db.add_message(os.urandom(8).hex(), "user", prompt, model="direct-intent")
            encrypted_db.add_message(os.urandom(8).hex(), "assistant", full_reply, model="direct-intent", tokens=15)
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
            if m_text and "<tool_name>" not in m_text and "Please respond with a JSON block" not in m_text:
                cleaned = re.sub(r"\[(Phenom Safety Gate|Tool|Action Blocked).*?\]", "", m_text).strip()
                if cleaned:
                    chat_messages.append({"role": role, "content": cleaned})
        chat_messages.append({"role": "user", "content": prompt})

        start_time = time.perf_counter()
        token_index = 0
        collected_tokens = []
        is_first_token = True

        try:
            if backend_type == "local":
                # Stream from Ollama chat endpoint with native ChatML token separation
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        OLLAMA_CHAT_URL,
                        json={
                            "model": model_name,
                            "messages": chat_messages,
                            "stream": True,
                            "keep_alive": -1,
                            "options": {
                                "temperature": 0.2,
                                "num_predict": 512,
                            }
                        }
                    ) as resp:
                        async for line in resp.aiter_lines():
                            if cancel_event and cancel_event.is_set():
                                yield {"type": "chat.cancelled", "payload": {"tokens_emitted": token_index}}
                                yield {"type": "state.change", "payload": {"state": "idle"}}
                                return

                            if not line:
                                continue
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                if is_first_token:
                                    is_first_token = False
                                    yield {"type": "state.change", "payload": {"state": "speaking"}}
                                token_index += 1
                                collected_tokens.append(token)
                                yield {"type": "chat.token", "payload": {"token": token, "index": token_index}}

                            if chunk.get("done"):
                                break
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
                        if is_first_token:
                            is_first_token = False
                            yield {"type": "state.change", "payload": {"state": "speaking"}}
                        token_index += 1
                        collected_tokens.append(token)
                        yield {"type": "chat.token", "payload": {"token": token, "index": token_index}}

        except Exception as e:
            yield {"type": "error", "payload": {"message": f"Inference error: {str(e)}"}}
            yield {"type": "state.change", "payload": {"state": "idle"}}
            return

        elapsed = time.perf_counter() - start_time
        tps = token_index / elapsed if elapsed > 0 else 0.0
        full_reply = "".join(collected_tokens)

        # 2. Check for Tool Call in Reply
        call_data = None
        for m in re.finditer(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", full_reply, re.DOTALL):
            try:
                candidate = json.loads(m.group(1))
                if isinstance(candidate, dict) and ("tool" in candidate or "action" in candidate or "app" in candidate):
                    call_data = candidate
                    break
            except Exception:
                continue

        if not call_data:
            for m in re.finditer(r"(\{[\s\S]*?\})", full_reply):
                try:
                    candidate = json.loads(m.group(1))
                    if isinstance(candidate, dict) and ("tool" in candidate or "action" in candidate or "app" in candidate):
                        call_data = candidate
                        break
                except Exception:
                    continue

        if not call_data:
            m_yt = re.search(r"youtube[-_]play\s+[\"']([^\"']+)[\"']", full_reply, re.IGNORECASE)
            if m_yt:
                call_data = {"tool": "youtube", "args": {"play": m_yt.group(1)}}
            else:
                m_op = re.search(r"(?:open|launch)[-_]?(?:app)?\s+[\"']([^\"']+)[\"']", full_reply, re.IGNORECASE)
                if m_op:
                    call_data = {"tool": "open_app", "args": {"app_name": m_op.group(1)}}



        if call_data:
            try:
                pass # call_data parsed above
                tool_name = call_data.get("tool")
                tool_args = call_data.get("args", {})
                if tool_name:
                    tool_name, tool_args = self._resolve_tool_alias(tool_name, tool_args)
                    yield {"type": "state.change", "payload": {"state": "thinking", "detail": f"Executing {tool_name}"}}
                    yield {"type": "chat.token", "payload": {"token": f"\n\n[Phenom Safety Gate: Requesting {tool_name}...]\n", "index": token_index + 1}}
                    
                    # Execute strictly through Safety Execution Engine
                    tool_result = await safety_engine.execute_tool(tool_name, tool_args)
                    
                    yield {"type": "state.change", "payload": {"state": "speaking"}}
                    res_val = tool_result.get('result')
                    if isinstance(res_val, dict) and 'briefing_markdown' in res_val:
                        result_msg = f"\n{res_val['briefing_markdown']}\n"
                    elif isinstance(res_val, dict) and 'message' in res_val and len(res_val.keys()) <= 3:
                        result_msg = f"\n{res_val['message']}\n"
                    elif tool_name == "open_app":
                        app_target = str(tool_args.get("app_name", ""))
                        if "youtube" in app_target.lower():
                            result_msg = "\nDone Bro! Opening YouTube for you. Enjoy the music!\n"
                        else:
                            clean_disp = app_target.split("\\")[-1].replace(".exe", "").title()
                            result_msg = f"\nDone Bro! {clean_disp} is now running.\n"
                    else:
                        result_msg = f"\nSab set hai Bro! {tool_name} executed successfully.\n"
                    yield {"type": "chat.token", "payload": {"token": result_msg, "index": token_index + 2}}
                    full_reply += f"\n{result_msg}"
            except Exception as tool_err:
                yield {"type": "chat.token", "payload": {"token": f"\n[Action Blocked or Failed: {tool_err}]", "index": token_index + 1}}
                full_reply += f"\n[Action Blocked: {tool_err}]"

        # 3. Post-Task Persistence
        encrypted_db.add_message(os.urandom(8).hex(), "user", prompt, model=model_name)
        encrypted_db.add_message(os.urandom(8).hex(), "assistant", full_reply, model=model_name, tokens=token_index)

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
