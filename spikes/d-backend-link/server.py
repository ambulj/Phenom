"""
Spike D: Backend Link Server
FastAPI + WebSocket streaming tokens from Ollama (Spike A).
Handles:
- chat.send: streams tokens with chat.token messages
- chat.cancel: halts token generation in under 1 second
- state.change: broadcasts orb state transitions
"""

import asyncio
import json
import time
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

app = FastAPI(title="Phenom Spike D Backend Link")

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"

class CancelableTask:
    def __init__(self):
        self.cancel_event = asyncio.Event()

current_tasks: dict[str, CancelableTask] = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(id(websocket))
    task_holder = CancelableTask()
    current_tasks[session_id] = task_holder
    active_stream_task: asyncio.Task | None = None

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            msg_id = msg.get("id", "msg-0")
            payload = msg.get("payload", {})

            if msg_type == "chat.send":
                prompt = payload.get("prompt", "")
                model = payload.get("model", "llama3:latest")
                
                # Reset cancellation event
                task_holder.cancel_event.clear()

                async def stream_tokens(p: str, m: str, req_id: str):
                    await websocket.send_json({
                        "id": req_id,
                        "type": "state.change",
                        "payload": {"state": "thinking"}
                    })
                    start_stream_time = time.perf_counter()
                    token_count = 0
                    first_token = True

                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            async with client.stream(
                                "POST",
                                OLLAMA_GENERATE_URL,
                                json={"model": m, "prompt": p, "stream": True}
                            ) as response:
                                async for line in response.aiter_lines():
                                    if task_holder.cancel_event.is_set():
                                        cancel_duration = time.perf_counter() - cancel_time
                                        await websocket.send_json({
                                            "id": req_id,
                                            "type": "chat.cancelled",
                                            "payload": {
                                                "tokens_emitted": token_count,
                                                "cancel_duration_ms": round(cancel_duration * 1000, 2)
                                            }
                                        })
                                        await websocket.send_json({
                                            "id": req_id,
                                            "type": "state.change",
                                            "payload": {"state": "idle"}
                                        })
                                        return

                                    if not line:
                                        continue
                                    chunk = json.loads(line)
                                    token = chunk.get("response", "")
                                    if token:
                                        if first_token:
                                            first_token = False
                                            await websocket.send_json({
                                                "id": req_id,
                                                "type": "state.change",
                                                "payload": {"state": "speaking"}
                                            })
                                        token_count += 1
                                        await websocket.send_json({
                                            "id": req_id,
                                            "type": "chat.token",
                                            "payload": {"token": token, "index": token_count}
                                        })
                                    if chunk.get("done"):
                                        break
                                        
                        elapsed = time.perf_counter() - start_stream_time
                        await websocket.send_json({
                            "id": req_id,
                            "type": "chat.done",
                            "payload": {
                                "tokens": token_count,
                                "duration_s": round(elapsed, 2),
                                "tps": round(token_count / elapsed, 1) if elapsed > 0 else 0
                            }
                        })
                        await websocket.send_json({
                            "id": req_id,
                            "type": "state.change",
                            "payload": {"state": "idle"}
                        })
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        await websocket.send_json({
                            "id": req_id,
                            "type": "error",
                            "payload": {"message": str(e)}
                        })

                if active_stream_task and not active_stream_task.done():
                    active_stream_task.cancel()
                active_stream_task = asyncio.create_task(stream_tokens(prompt, model, msg_id))

            elif msg_type == "chat.cancel":
                cancel_time = time.perf_counter()
                task_holder.cancel_event.set()
                if active_stream_task and not active_stream_task.done():
                    active_stream_task.cancel()
                    cancel_duration = time.perf_counter() - cancel_time
                    await websocket.send_json({
                        "id": msg_id,
                        "type": "chat.cancelled",
                        "payload": {
                            "cancel_duration_ms": round(cancel_duration * 1000, 2)
                        }
                    })
                    await websocket.send_json({
                        "id": msg_id,
                        "type": "state.change",
                        "payload": {"state": "idle"}
                    })

    except WebSocketDisconnect:
        pass
    finally:
        if active_stream_task and not active_stream_task.done():
            active_stream_task.cancel()
        current_tasks.pop(session_id, None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
