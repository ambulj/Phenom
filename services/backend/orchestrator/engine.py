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

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

SYSTEM_PROMPT_TEMPLATE = """You are Phenom, a personal Windows 11 desktop assistant.
Personality: Witty, playful, Jarvis-style sidekick. Confident and warm, never smug.
Humor is light and short; at most one brief quip per reply, and none during errors, warnings, or destructive actions.
Clarity first: deliver the answer or action, then the flourish.

Permanent Rules:
1. You act only through tools. Every tool execution is subject to safety validation.
2. Delete means send to Recycle Bin. Never permanent delete.
3. Finance is informational only: no trading, no buy/sell advice.
4. If a request looks risky or irreversible, politely warn the user once, explain the risk, offer a safer option, and proceed with their choice.
5. Never pretend to have executed a command without receiving a tool result.

Active Learned Rules:
{learned_rules}

Available Tools:
{tool_descriptions}

To call a tool, respond ONLY with a JSON block in this exact format:
```json
{{"tool": "<tool_name>", "args": {{<arguments>}}}}
```
Otherwise, respond naturally in English. Keep voice/orb replies concise and crisp.
"""

def build_system_prompt() -> str:
    # Build tool descriptions
    tool_lines = []
    for name, tool_def in registry.list_all().items():
        fields = list(tool_def.args_schema.model_fields.keys())
        tool_lines.append(f"- {name}({', '.join(fields)}): {tool_def.description} [Tier {tool_def.tier}]")
    tools_str = "\n".join(tool_lines)

    rules_str = learned_rules.format_rules_for_prompt() or "(None yet)"
    return SYSTEM_PROMPT_TEMPLATE.format(learned_rules=rules_str, tool_descriptions=tools_str)

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

        # RAG: Retrieve relevant memory context from Vector Store
        memory_context = ""
        try:
            from services.backend.memory.vector_store import vector_store
            doc_matches = vector_store.search(prompt, top_k=2)
            if doc_matches and doc_matches[0]["score"] > 0.45:
                sources = "\n".join([f"- [{m['filename']}] (Score: {m['score']}): {m['snippet']}" for m in doc_matches])
                memory_context = f"\nRelevant Memory & Document Citations:\n{sources}\n"
        except Exception:
            pass

        system_prompt = build_system_prompt()
        history = encrypted_db.get_recent_messages(limit=6)
        history_context = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])

        full_prompt = f"{system_prompt}\n{memory_context}\nRecent History:\n{history_context}\n\nUser: {prompt}\nAssistant:"

        start_time = time.perf_counter()
        token_index = 0
        collected_tokens = []
        is_first_token = True

        try:
            if backend_type == "local":
                # Stream from Ollama
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        OLLAMA_GENERATE_URL,
                        json={"model": model_name, "prompt": full_prompt, "stream": True, "options": {"temperature": 0.2}}
                    ) as resp:
                        async for line in resp.aiter_lines():
                            if cancel_event and cancel_event.is_set():
                                yield {"type": "chat.cancelled", "payload": {"tokens_emitted": token_index}}
                                yield {"type": "state.change", "payload": {"state": "idle"}}
                                return

                            if not line:
                                continue
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
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
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
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
        tool_call_match = re.search(r"```json\s*(\{.*?\})\s*```", full_reply, re.DOTALL)
        if not tool_call_match and full_reply.strip().startswith("{") and full_reply.strip().endswith("}"):
            tool_call_match = re.search(r"(\{.*\})", full_reply, re.DOTALL)

        if tool_call_match:
            try:
                call_data = json.loads(tool_call_match.group(1))
                tool_name = call_data.get("tool")
                tool_args = call_data.get("args", {})
                if tool_name:
                    yield {"type": "state.change", "payload": {"state": "thinking", "detail": f"Executing {tool_name}"}}
                    yield {"type": "chat.token", "payload": {"token": f"\n\n[Phenom Safety Gate: Requesting {tool_name}...]\n", "index": token_index + 1}}
                    
                    # Execute strictly through Safety Execution Engine
                    tool_result = await safety_engine.execute_tool(tool_name, tool_args)
                    
                    yield {"type": "state.change", "payload": {"state": "speaking"}}
                    result_msg = f"[Tool {tool_name} Result: {json.dumps(tool_result.get('result'))}]\nAll set."
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
