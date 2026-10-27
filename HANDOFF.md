# HANDOFF.md

Updated at the conclusion of Phase 0 (Feasibility Spikes).

## Current phase
Phase 0: Feasibility Spikes (COMPLETE)

## How to run
```bash
# Spike A (Local Model Benchmark)
python spikes/a-local-model/benchmark.py llama3:latest
python spikes/a-local-model/benchmark.py llama3:8b-instruct-q8_0

# Spike B (Cloud Model Nemotron)
$env:NVIDIA_API_KEY = "nvapi-..."
python spikes/b-cloud-model/test_nemotron.py

# Spike C (Orb Renderer & Benchmark)
cd spikes/c-orb
npm start
python spikes/c-orb/measure_orb.py

# Spike D (FastAPI WebSocket & Cancellation)
python spikes/d-backend-link/server.py
python spikes/d-backend-link/test_client.py

# Spike E (SQLCipher & Windows Credential Manager)
python spikes/e-encryption/test_encryption.py

# Spike F (Voice Feasibility: TTS, Whisper CUDA, Wake Word)
python spikes/f-voice/test_voice.py
```

## What exists
- `spikes/a-local-model/`:
  - `benchmark.py`: Complete test runner for first-token latency, throughput (tps), VRAM consumption, 20-prompt tool-calling JSON schema compliance, and 3,000-word document summarization.
  - `results_llama3_latest.json`: Empirical results for 4-bit quantization.
  - `results_llama3_8b-instruct-q8_0.json`: Empirical results for 8-bit quantization.
  - `README.md`: Documentation and instructions.
- `spikes/b-cloud-model/`:
  - `test_nemotron.py`: NVIDIA build.nvidia.com OpenAI-compatible client, streaming test, timeout testing, error guard validation.
  - `results.json`: Output metrics and error path logs.
  - `README.md`: Documentation and instructions.
- `spikes/c-orb/`:
  - `package.json`: Electron 33.4.11 and Three.js dependencies.
  - `main.js`: Electron main process.
  - `index.html`: UI container, HUD, and 5-mode interactive state buttons.
  - `orb.js`: 6,000-particle WebGL cloud, state interpolations (< 500 ms), and corner shrink handler.
  - `measure_orb.py`: Automated performance sampler.
  - `results.json`: 60 FPS verification and GPU load metrics.
  - `README.md`: Documentation and instructions.
- `spikes/d-backend-link/`:
  - `server.py`: FastAPI server with WebSocket `/ws`, streaming Ollama tokens, handling `chat.cancel`, broadcasting orb states.
  - `test_client.py`: Automated client testing token stream and measuring cancel latency.
  - `results.json`: 0.70 ms cancel verification.
  - `README.md`: Documentation and instructions.
- `spikes/e-encryption/`:
  - `test_encryption.py`: Key generator, Windows Credential Manager reader/writer (`win32cred`), SQLCipher database creator, unencrypted access rejection verifier.
  - `test_encrypted.db`: Verified encrypted SQLite file.
  - `results.json`: Key roundtrip, header entropy, and decryption proof.
  - `README.md`: Documentation and instructions.
- `spikes/f-voice/`:
  - `test_voice.py`: SAPI5 male TTS benchmark, `faster-whisper` tiny.en on CUDA with cublas DLL resolution, `openWakeWord` ONNX streaming detection.
  - `test_speech.wav`: Reference audio sample.
  - `results.json`: TTS/STT latency and accuracy benchmarks.
  - `README.md`: Documentation and instructions.
- `SPIKES.md`: Comprehensive table of all results, hardware discoveries, and recommendations.

## Decisions made
- **Quantization (2026-10-27)**: Use 4-bit quantization (`llama3:latest` Q4_0 / Q4_K_M) instead of 8-bit. Due to the laptop GPU having 6 GB VRAM, 8-bit models spill 55% of layers into host RAM, cutting throughput from 14.85 tps down to 5.63 tps. 4-bit maintains 100% JSON/tool accuracy while running 2.6x faster.
- **Local TTS (2026-10-27)**: Use Windows SAPI5 (`Microsoft David Desktop`) for local male voice. Measured 89.67 ms to first audio with 0 VRAM usage.
- **Local STT (2026-10-27)**: Use `faster-whisper` with `tiny.en` on CUDA (float16). Measured 354.9 ms median latency for ~8s audio (0.045x real-time factor).
- **Windows Credential Manager (2026-10-27)**: Use native `win32cred` (`CRED_TYPE_GENERIC`) from `pywin32`. Roundtrip storage of 256-bit DB keys verified.
- **SQLCipher Engine (2026-10-27)**: Standardize on `sqlcipher3-wheels` 0.5.7 (SQLCipher v4).

## Dependencies added
- `sqlcipher3-wheels` (0.5.7): Pre-compiled SQLCipher v4 bindings for Windows Python 3.11.
- `faster-whisper` (1.2.1) + `ctranslate2` (4.8.4): Fast, GPU-accelerated local transcription engine.
- `openwakeword` (0.6.0): Local ONNX wake word detection without cloud dependencies.
- `electron` (33.4.11) + `three` (0.170.0): Desktop UI container and 3D particle orb system.

## Known issues
- `NVIDIA_API_KEY` was missing from the current system environment during Spike B; API error paths (HTTP 403, timeout) were tested and verified. User should provide their key when ready.
- Hardware VRAM is 6 GB (NVIDIA RTX 3050 Laptop GPU) rather than the 8+ GB specified in initial assumptions. Fully mitigated by selecting 4-bit quantization.

## Open questions for the user
1. Would you like to provide an `NVIDIA_API_KEY` now or configure it via the Phase 1 settings/Credential Manager?
   *(Recommended default: Configure via environment variable or Windows Credential Manager in Phase 1).*

## Next
Phase 1: Core. Scaffold repo layout, build Safety layer first with four tiers and Guardian kill switch, create FastAPI WebSocket backend, model router with private tag filtering, tool implementations, and Electron Fluent UI with Three.js particle orb.
