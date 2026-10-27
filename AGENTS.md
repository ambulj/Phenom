# AGENTS.md: Phenom project rules

Read this file at the start of every session. It applies to every phase.

## 1. What Phenom is
Phenom is a personal Windows 11 desktop assistant for one user. It chats and speaks, controls files, apps, the browser and the screen, remembers things, and can be reached remotely through Telegram. Personality: witty, playful, Jarvis-style, male voice. English only.

## 2. Stack (do not change without asking)
| Layer | Choice |
| --- | --- |
| Desktop app | Electron + React + Vite + TypeScript, Fluent UI |
| Orb | Three.js particle cloud |
| Backend | Python FastAPI with a WebSocket link to the UI |
| Local model | 8B instruct on the NVIDIA GPU (8 GB VRAM or more) via Ollama or llama.cpp, CUDA |
| Cloud model | Nemotron through the NVIDIA build.nvidia.com API |
| Memory | SQLite + SQLCipher, key in Windows Credential Manager |
| Notes | Obsidian vault inside the project folder |
| Documents | python-docx, openpyxl, python-pptx, reportlab |
| Browser | Playwright |
| Speech | Local wake word, local Whisper, local male TTS |

## 3. Repo layout
```
phenom/
  AGENTS.md  SAFETY.md  ARCHITECTURE.md  PERSONALITY.md
  HANDOFF.md  SPIKES.md
  phases/PHASE_0.md ... PHASE_7.md
  apps/desktop/        Electron + React app
  services/backend/    FastAPI, router, safety, tools, memory
  vault/               Obsidian vault (Phase 4)
  spikes/              throwaway proofs of concept (Phase 0 only)
```
Never restructure the layout without asking.

## 4. Permanent rules
1. The model never calls a tool directly. Every call goes through the Safety layer (see SAFETY.md), which classifies it by risk tier and enforces confirmation.
2. Every action is written to the action log.
3. The Guardian kill switch (button plus global hotkey) halts everything immediately, even if the model is hung.
4. Private files and text never reach a cloud model without a previewed approval. If unsure, treat it as private.
5. Finance is informational only. Never place trades. Never suggest buying or selling.
6. Photos are indexed and searched only. Never move, rename, edit or delete them.
7. Delete means recycle bin. Never permanent delete.
8. Payments are impossible by construction. Fill carts and stop. Never type or store passwords.
9. Email: drafts only, never send. Calendar: create events only, never delete or edit others' events.
10. If a request looks risky or likely wrong, warn politely once, then follow the user's decision unless it is Tier 3 and not allowed.
11. Secrets live in environment variables or Credential Manager. Never in code, logs, memory or chat.
12. Work only on the current phase. If a later feature seems needed, write it in HANDOFF.md under "Next" and do not build it.

## 5. Working agreement
- **Plan first.** Start each phase by reading `phases/PHASE_N.md`, then write a short plan (files to create, order, risks) and proceed unless something is unclear. Ask the user only about real ambiguities, with a recommended default.
- **Small steps.** One step at a time, tests with each step, commit after each step with a clear message.
- **Safety before tools.** No tool is added before the Safety layer exists to wrap it.
- **Evidence.** Never claim something works without showing a test or a run. Say "not verified" when it is not.
- **No silent fallbacks.** If something fails, surface the error. Never hide it behind a mock.
- **Typed everything.** TypeScript strict mode. Python type hints with mypy or pyright. Pydantic models for every message and tool schema.
- **Dependencies.** Pin versions. Prefer well-maintained libraries. Note the reason for each new dependency in HANDOFF.md.
- **Privacy by default.** Logs must never contain file contents, email bodies, passwords, API keys, or audio.

## 6. Definition of done for a phase
Every item in the phase's "Done criteria" is PASS with evidence, tests pass, HANDOFF.md and SAFETY.md are updated, and the user has approved.

## 7. Finish protocol (end of every phase)
1. List each done criterion as PASS or FAIL with evidence.
2. Show test results.
3. Update HANDOFF.md and SAFETY.md.
4. List known issues, open questions, and anything you were unsure about.
5. Stop and wait for approval. Do not start the next phase.
