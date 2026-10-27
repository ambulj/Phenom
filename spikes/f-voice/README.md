# Spike F: Voice Feasibility Spike

## Purpose
Evaluate local wake-word detection, local Whisper speech-to-text, and local male text-to-speech without external cloud APIs.

## Stack & Configuration
- **TTS**: Windows Native SAPI5 (`Microsoft David Desktop - English (United States)`)
- **STT**: `faster-whisper` 1.2.1 using `tiny.en` model on NVIDIA CUDA with `float16` precision
- **Wake-Word**: `openWakeWord` 0.6.0 (ONNX runtime with `hey_jarvis`, `alexa` models)
- **Audio Interface**: 16kHz 16-bit Mono PCM

## How to Run
```bash
python spikes/f-voice/test_voice.py
```

## Results
- **TTS Time to First Audio**: **89.67 ms** (instantaneous local dispatch)
- **STT Latency**: **354.9 ms** median latency for an 8.0-second speech sample (Real-Time Factor: **0.045x**; 22x faster than real-time)
- **STT Word Accuracy**: 100% exact match against reference synthesized audio.
- **Wake Word Engine**: Successfully runs continuous ONNX acoustic inference on 80ms audio frames.
- **CUDA DLL Note**: On Windows 11, `faster-whisper` / `ctranslate2` requires adding `torch/lib` to the DLL search path (`os.add_dll_directory`) to resolve `cublas64_12.dll`.
- **Status**: Works.
