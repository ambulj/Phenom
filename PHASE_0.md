# PHASE 0: Feasibility spikes

## Objective
Find out what breaks before building on it. A failed spike is a valid, useful result.

## Read first
AGENTS.md, ARCHITECTURE.md, SAFETY.md (sections 5 and 7), SPIKES.md.

## Rules for this phase
Work only inside `spikes/`. No product code. Each spike is independent, small, and can be thrown away. Record every number in SPIKES.md.

## Spikes

### A. Local model
1. Install Ollama (or build llama.cpp with CUDA) and run an 8B instruct model on the NVIDIA GPU.
2. Test a 4-bit and an 8-bit quantization.
3. Measure first-token latency, tokens per second, and VRAM use, each over 5 runs, reporting the median.
4. Tool-call reliability: send 20 prompts that need a JSON tool call (for example `{"tool":"list_files","args":{"path":"..."}}`). Report how many returned valid JSON and the correct tool.
5. Test a 3,000-word document summary and report time and quality.

### B. Cloud model
1. Call Nemotron through the build.nvidia.com API, OpenAI-compatible endpoint, key from the `NVIDIA_API_KEY` environment variable.
2. Measure latency and streaming speed; confirm streaming works.
3. Record rate limits, context length, and error behaviour (bad key, timeout).

### C. Orb
1. Electron window with a Three.js particle cloud (at least 5,000 particles) at 60 fps.
2. Five modes switched by buttons: idle, listening, thinking, speaking, halted, with the colours and behaviours in ARCHITECTURE.md section 5.
3. Smooth transition between modes in under 500 ms.
4. Shrink animation to a corner icon.
5. Report GPU and CPU use while idle.

### D. Backend link
1. FastAPI plus WebSocket to the Electron window.
2. Stream tokens from Spike A to the window.
3. A `chat.cancel` message must stop generation within 1 second.

### E. Encryption
1. Create a SQLCipher database from Python.
2. Store its key in Windows Credential Manager and read it back on the next run.
3. Show that the file is unreadable without the key.

### F. Voice feasibility
1. Run a local wake-word detector on live microphone input.
2. Run local Whisper on a 10-second recording.
3. Report CPU and GPU use while listening and the time from end of speech to text.
4. Try one local male TTS voice and report time to first audio.

## Deliverables
`spikes/a-local-model/` through `spikes/f-voice/`, each with a README (how to run) and results; a completed SPIKES.md with a recommendation.

## Done criteria
- [ ] Six spikes run, each with a result row in SPIKES.md
- [ ] Numbers recorded, versions noted
- [ ] Every blocker named with a proposed alternative
- [ ] Recommendation written: stack changes, quantization to use, risks for Phases 1 and 2

## Out of scope
Any product code, UI polish, or features.

## Finish
Follow the finish protocol in AGENTS.md section 7 and stop.
