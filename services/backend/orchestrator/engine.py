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
1. Action Execution: When the user requests ANY action, media control, playback change, volume adjustment, app launch, news briefing, weather, calculation, reminder, or system task — whether phrased in English or Hinglish (e.g. "Spotify pause kar do", "Volume badhao", "News sunao", "Chrome kholo", "Calculate this"):
   Output ONLY the JSON execution block immediately:
```json
{{"tool": "<tool_name>", "args": {{<arguments>}}}}
```
   Do NOT provide conversational preamble, greetings, or meta-explanations. Output the tool JSON immediately.

2. General Conversation: When the user greets you (e.g. "hi", "kya haal hai Bro", "hello") or makes casual conversation, respond in 1-2 natural, punchy Hinglish sentences addressing the user as "Bro". Never mention JSON, tools, or schemas to the user. Never offer canned system status reports unless explicitly asked.

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
    target_model = model_name or os.environ.get("PHENOM_LOCAL_MODEL", "phenom-jarvis:latest")
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

        yield {"type": "state.change", "payload": {"state": "thinking"}}

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
        for m in re.finditer(r"```json\s*(\{.*?\})\s*```", full_reply, re.DOTALL):
            try:
                candidate = json.loads(m.group(1))
                if isinstance(candidate, dict) and "tool" in candidate:
                    t_name = str(candidate.get("tool", "")).strip()
                    if t_name and not t_name.startswith("<") and not t_name.endswith(">"):
                        call_data = candidate
                        break
            except Exception:
                continue

        if not call_data:
            for m in re.finditer(r"(\{[\s\S]*?\"tool\"\s*:\s*\"([^\"]+)\"[\s\S]*?\})", full_reply):
                try:
                    candidate = json.loads(m.group(1))
                    if isinstance(candidate, dict) and "tool" in candidate:
                        t_name = str(candidate.get("tool", "")).strip()
                        if t_name and not t_name.startswith("<") and not t_name.endswith(">") and t_name != "<tool_name>":
                            call_data = candidate
                            break
                except Exception:
                    continue
        if not call_data and full_reply.strip().startswith("{") and full_reply.strip().endswith("}"):
            try:
                candidate = json.loads(full_reply.strip())
                if isinstance(candidate, dict) and "tool" in candidate:
                    t_name = str(candidate.get("tool", "")).strip()
                    if t_name and not t_name.startswith("<") and not t_name.endswith(">"):
                        call_data = candidate
            except Exception:
                pass



        if call_data:
            try:
                pass # call_data parsed above
                tool_name = call_data.get("tool")
                tool_args = call_data.get("args", {})
                if tool_name:
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
                    else:
                        result_msg = f"[Tool {tool_name} Result: {json.dumps(res_val)}]\nAll set."
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
