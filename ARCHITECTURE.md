# ARCHITECTURE.md

## 1. Components
```
Electron app (React + Fluent UI + Three.js orb)
   |  WebSocket (typed JSON messages)
FastAPI backend
   |-- Orchestrator: conversation loop, tool-call loop
   |-- Router: local 8B vs cloud Nemotron
   |-- Safety layer: classify, confirm, log, kill switch (Guardian)
   |-- Tools: files, apps, browser, screen, documents, integrations
   |-- Memory: SQLCipher DB, vector index, Obsidian vault
   |-- Voice: wake word, STT, TTS
   |-- Scheduler: modes, recurring tasks
   |-- Telegram bridge (Phase 6)
```

## 2. Request flow
1. Input arrives (typed, voice, Telegram, scheduler) and is tagged with its source.
2. The orchestrator builds the prompt: system prompt (PERSONALITY.md), relevant memory, learned rules, current mode.
3. The Router picks the model (rules below) and streams tokens to the UI.
4. If the model asks for a tool, the call goes to the Safety layer: classify, preview, confirm if needed, log, run, log result.
5. Tool results return to the model; the loop continues until a final reply.
6. After the task, memory is saved automatically (summary, facts, learned rules).

## 3. Router rules
| Condition | Model |
| --- | --- |
| Default | Local 8B |
| Any input labelled private | Local 8B, always |
| Long shareable input beyond the local context or quality limit | Cloud Nemotron, after previewed approval |
| Cloud unreachable or approval denied | Local 8B with chunking, and say so |
Every decision is logged with its reason.

## 4. WebSocket protocol (all messages have `id`, `type`, `ts`)
- UI to backend: `chat.send`, `chat.cancel`, `confirm.reply`, `settings.update`, `killswitch.trigger`, `mode.set`
- Backend to UI: `chat.token`, `chat.done`, `state.change` (idle|listening|thinking|speaking|halted), `tool.request`, `confirm.request`, `log.entry`, `rules.updated`, `error`
Define each as a Pydantic model in the backend and a TypeScript type in the app, generated from one schema so they never drift.

## 5. Orb states
| State | Colour | Particle behaviour |
| --- | --- | --- |
| idle | calm blue | slow drift, low density motion |
| listening | teal | gentle pulse toward the centre |
| thinking | violet | swirl around the core |
| speaking | amber | bursts timed to speech amplitude |
| halted | red | frozen, dim |
Panel open: the orb shrinks to a corner icon with the same colour and a small animation.

## 6. Memory
Tables: `messages`, `facts`, `learned_rules`, `approvals_remembered`, `action_log`, `watchlist`, `schedules`, `file_index`, `settings`. Encrypted with SQLCipher; the key is in Credential Manager under `Phenom/db-key`. The vector index is stored in the same encrypted store or an encrypted file beside it. The Obsidian vault is plain Markdown in `vault/`.

## 7. Configuration
`config.toml` for non-secret settings (hotkeys, folders, model names). Secrets only in environment variables or Credential Manager. A settings panel writes to config and never displays secrets.
