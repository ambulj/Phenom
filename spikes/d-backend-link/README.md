# Spike D: Backend Link & WebSocket Cancellation

## Purpose
Verify that:
1. FastAPI can serve a typed WebSocket endpoint connecting the Electron UI to local Ollama inference.
2. Token generation streams smoothly chunk-by-chunk to the client.
3. A `chat.cancel` signal halts model generation in under 1 second (< 1000 ms).

## Protocol Specification
- **Client -> Server**:
  - `{"id": "...", "type": "chat.send", "payload": {"prompt": "...", "model": "..."}}`
  - `{"id": "...", "type": "chat.cancel", "payload": {}}`
- **Server -> Client**:
  - `{"id": "...", "type": "state.change", "payload": {"state": "thinking|speaking|idle"}}`
  - `{"id": "...", "type": "chat.token", "payload": {"token": "...", "index": N}}`
  - `{"id": "...", "type": "chat.cancelled", "payload": {"cancel_duration_ms": N}}`
  - `{"id": "...", "type": "chat.done", "payload": {"tokens": N, "duration_s": N, "tps": N}}`

## How to Run
```bash
# 1. Start backend server in one terminal:
python spikes/d-backend-link/server.py

# 2. Run automated test client in another terminal:
python spikes/d-backend-link/test_client.py
```
