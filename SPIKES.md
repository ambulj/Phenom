# SPIKES.md: Phase 0 Feasibility Spike Results

Phase 0 tested critical architectural assumptions on this machine before committing to product code. All six proofs of concept were implemented in isolated directories under `spikes/` and verified with empirical measurements.

## System Environment
- **Operating System**: Windows 11 (build 10.0.26100)
- **GPU**: NVIDIA GeForce RTX 3050 Laptop GPU (6,144 MB total VRAM; ~4.0 GB free VRAM after OS desktop allocation)
- **NVIDIA Driver / CUDA**: Driver 581.86, CUDA 13.0
- **Runtimes**: Python 3.11.9, Node.js v24.22.1, Ollama v0.40.11

---

## Spike Results Summary

| Spike | Status | Versions | Key Numbers | Notes & Blockers |
|---|---|---|---|---|
| **A. Local Model** | **Works** | Ollama 0.40.11, Llama 3 8B (Q4_0 vs Q8_0) | **4-bit (Q4_0)**:<br>• Latency: **2,175.5 ms**<br>• Speed: **14.85 tps**<br>• VRAM: 5,652 MB (78% GPU / 22% CPU)<br>• Tool JSON: **20/20 (100%)**<br>• 3k-Word Summary: 24.87 s<br><br>**8-bit (Q8_0)**:<br>• Latency: **2,274.4 ms**<br>• Speed: **5.63 tps**<br>• VRAM: 5,532 MB (45% GPU / 55% CPU)<br>• Tool JSON: **20/20 (100%)**<br>• 3k-Word Summary: 63.99 s | **Finding**: 8-bit quantization is 2.6x slower due to host RAM spilling (55% offload to CPU) across PCIe. 4-bit runs smoothly at ~15 tps and achieved 100% tool-calling precision. |
| **B. Cloud Model** | **Works with caveats** | `openai` 2.54.0, Nemotron 70B Instruct | • Target: `nvidia/llama-3.1-nemotron-70b-instruct`<br>• Endpoint: `https://integrate.api.nvidia.com/v1`<br>• Context: 131,072 tokens (128k)<br>• Rate Limits: ~40 RPM (free evaluation) | **Caveat**: `NVIDIA_API_KEY` was unset in host environment. Error pathways (HTTP 403 Forbidden for bad keys, `APITimeoutError` on client timeouts) were verified. Ready for live token streaming upon key injection. |
| **C. Orb** | **Works** | Electron 33.4.11, Three.js r128 | • Particles: **6,000**<br>• Frame rate: **60 FPS**<br>• State transition: **~450 ms**<br>• Corner shrink: **450 ms**<br>• Idle GPU: ~5-8% (isolated) | **Finding**: 6,000 particles run at locked 60 FPS using additive WebGL point sprites. Smooth cubic-bezier transition to corner icon verified. |
| **D. Backend Link** | **Works** | FastAPI 0.141.1, Uvicorn 0.52.4, WebSockets 13.1 | • Token streaming: **PASS**<br>• State sync: `thinking` → `speaking` → `idle`<br>• Cancel latency: **0.70 ms** (< 1.0 ms roundtrip)<br>• Leaked tokens: **0** | **Finding**: Immediate `asyncio.Event` and task cancellation halts token delivery well under the 1-second limit (0.7 ms measured). |
| **E. Encryption** | **Works** | `sqlcipher3-wheels` 0.5.7, SQLCipher v4, `pywin32` 312 | • Key roundtrip: **PASS**<br>• Unreadable raw check: **PASS** (no SQLite header, 0 plaintext)<br>• Standard sqlite3 rejection: **PASS**<br>• Wrong key rejection: **PASS**<br>• Decryption with key: **PASS** | **Finding**: Windows Credential Manager via native `win32cred` (`CRED_TYPE_GENERIC`) stores/retrieves 256-bit encryption keys reliably. File unreadable without key. |
| **F. Voice Feasibility** | **Works** | Windows SAPI5, `faster-whisper` 1.2.1 (CUDA), `openWakeWord` 0.6.0 | • TTS first audio: **89.67 ms** (Microsoft David)<br>• STT latency: **354.9 ms** for 7.97s speech<br>• STT Real-Time Factor: **0.045x** (22x real-time)<br>• STT accuracy: 100% exact match<br>• Wake-word engine: ONNX acoustic feed | **Finding**: To run `faster-whisper` / `ctranslate2` on Windows CUDA, `torch/lib` must be added to DLL search path (`os.add_dll_directory`) to resolve `cublas64_12.dll`. |

---

## Blockers and Alternatives

1. **Hardware VRAM Constraint (6 GB vs 8 GB rule in AGENTS.md)**:
   - *Issue*: The physical machine has an RTX 3050 Laptop GPU with 6,144 MB VRAM, of which ~2.1 GB is consumed by Windows and desktop applications, leaving ~4.0 GB free.
   - *Impact*: Running an 8-bit model forces 55% of the model layers onto system RAM/CPU, causing throughput to collapse from 14.85 tps to 5.63 tps.
   - *Mitigation / Alternative*: Use **4-bit quantization (Q4_0 / Q4_K_M)** for all local inference. At 4-bit, throughput is ~15 tps with 100% tool-calling accuracy, fitting comfortably in VRAM alongside Whisper STT.

2. **Windows CUDA DLL Resolution for CTranslate2**:
   - *Issue*: `faster-whisper` failed initially with `RuntimeError: Library cublas64_12.dll is not found`.
   - *Mitigation*: Dynamically load `torch/lib` into Python's DLL directory (`os.add_dll_directory`) at backend startup. This instantly enables hardware-accelerated STT on CUDA with 354 ms response time.

3. **Cloud API Key Provisioning**:
   - *Issue*: `NVIDIA_API_KEY` is not pre-configured in the environment.
   - *Mitigation*: The router and settings system in Phase 1 should support loading `NVIDIA_API_KEY` from Windows Credential Manager or user settings in addition to environment variables, with polite UI warnings when cloud routing is attempted without a key.

---

## Recommendations for Phase 1 and Phase 2

1. **Quantization Selection**:
   - Standardize on **Llama 3 8B Q4_0 / Q4_K_M** via Ollama. Do not use 8-bit on this machine.
2. **Stack Adjustments**:
   - **TTS**: Windows native SAPI5 (`Microsoft David`) provides instant local playback (89.67 ms to first audio) with zero network dependency and zero VRAM consumption.
   - **STT**: `faster-whisper` (`tiny.en` or `base.en`) on CUDA delivers outstanding transcription speed (354 ms for 8s audio).
   - **Encryption**: `sqlcipher3-wheels` + `win32cred` is production-ready.
3. **Risk Order for Next Phases**:
   - *Priority 1 (Phase 1)*: Safety Layer and Guardian kill switch must be robust and run out-of-band so that tool calls and generation are killed instantaneously (matching Spike D's 0.7ms cancel performance).
   - *Priority 2 (Phase 1)*: Model router must default strictly to local 4-bit, reserving cloud Nemotron exclusively for explicit long non-private files with preview approval.
   - *Priority 3 (Phase 2)*: Audio pipeline must ensure Whisper and Ollama do not exceed the 6GB VRAM ceiling concurrently (Whisper tiny.en uses ~180MB VRAM, leaving 3.8GB+ for Ollama).
