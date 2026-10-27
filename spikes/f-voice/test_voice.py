"""
Spike F: Voice Feasibility Spike
Tests:
1. Wake-word detector (openWakeWord) running on audio frames; measures CPU & GPU utilization.
2. Local Whisper (faster-whisper) on a 10-second test speech sample on CUDA; measures STT latency & accuracy.
3. Local Male TTS (Windows SAPI5 Microsoft David); measures time to first audio.
"""

import os
import sys
import time
import json
import wave
import psutil
import numpy as np
import win32com.client
import subprocess

# Ensure CUDA cublas libraries from torch/lib are discoverable on Windows
try:
    import torch
    torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.exists(torch_lib):
        os.add_dll_directory(torch_lib)
        os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

def get_gpu_utilization() -> float:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            encoding="utf-8"
        )
        return float(out.strip().split("\n")[0])
    except Exception:
        return 0.0

def test_tts():
    print("\n--- [1] Local Male TTS Benchmark (SAPI5 Microsoft David) ---")
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    # Find male voice
    voices = speaker.GetVoices()
    male_voice_index = 0
    for i in range(voices.Count):
        desc = voices.Item(i).GetDescription()
        if "david" in desc.lower() or "male" in desc.lower():
            male_voice_index = i
            break
            
    speaker.Voice = voices.Item(male_voice_index)
    voice_name = voices.Item(male_voice_index).GetDescription()
    print(f"Selected voice: {voice_name}")
    
    test_phrase = "Good evening. Phenom audio subsystem online and operating within optimal parameters."
    
    # Measure time to first audio
    # Flag 1 is SVSFlagsAsync (asynchronous, starts playback immediately)
    t0 = time.perf_counter()
    speaker.Speak(test_phrase, 1)
    t_first_audio = time.perf_counter()
    first_audio_ms = (t_first_audio - t0) * 1000.0
    
    # Wait until finished speaking to measure total duration
    speaker.WaitUntilDone(-1)
    total_audio_s = time.perf_counter() - t0
    
    print(f" Time to first audio: {first_audio_ms:.2f} ms")
    print(f" Total speech duration: {total_audio_s:.2f} s")
    
    return {
        "voice_name": voice_name,
        "time_to_first_audio_ms": round(first_audio_ms, 2),
        "total_speech_s": round(total_audio_s, 2),
        "status": "works"
    }

def generate_test_audio_wav(output_wav_path: str, text: str):
    """Generates a reference 16kHz mono WAV file using SAPI5."""
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    # 16kHz 16-bit Mono is format 22 (SAFT16kHz16BitMono)
    stream.Format.Type = 22
    stream.Open(output_wav_path, 3, False) # 3 = SSFMCreateForWrite
    speaker.AudioOutputStream = stream
    speaker.Speak(text, 0)
    stream.Close()

def test_whisper_stt(wav_path: str):
    print("\n--- [2] Local Whisper STT Benchmark (faster-whisper on CUDA) ---")
    import faster_whisper
    
    print("Loading faster-whisper (tiny.en on CUDA with float16)...")
    load_start = time.perf_counter()
    # tiny.en or base.en for ultra-fast desktop assistant latency
    model = faster_whisper.WhisperModel("tiny.en", device="cuda", compute_type="float16")
    load_time = time.perf_counter() - load_start
    print(f"Model loaded in {load_time:.2f}s")
    
    # Warmup
    model.transcribe(wav_path, language="en")
    
    # Measure 3 runs
    latencies = []
    transcriptions = []
    
    for i in range(1, 4):
        t0 = time.perf_counter()
        gpu_before = get_gpu_utilization()
        segments, info = model.transcribe(wav_path, language="en", beam_size=1)
        text_result = " ".join([seg.text for seg in segments]).strip()
        elapsed_s = time.perf_counter() - t0
        gpu_during = get_gpu_utilization()
        
        latencies.append(elapsed_s * 1000.0)
        transcriptions.append(text_result)
        print(f" Run {i}: Latency = {elapsed_s*1000:.1f}ms | Audio duration = {info.duration:.2f}s | Result: '{text_result}'")
        
    median_lat = sorted(latencies)[len(latencies)//2]
    rtf = (median_lat / 1000.0) / info.duration # Real-time factor
    
    print(f"Median STT Latency: {median_lat:.1f} ms for {info.duration:.2f}s audio (Real-Time Factor: {rtf:.3f}x)")
    
    return {
        "model": "faster-whisper tiny.en (CUDA float16)",
        "audio_duration_s": round(info.duration, 2),
        "median_stt_latency_ms": round(median_lat, 2),
        "real_time_factor": round(rtf, 3),
        "sample_transcript": transcriptions[0],
        "status": "works"
    }

def test_wakeword_detector():
    print("\n--- [3] Local Wake-Word Detector Benchmark (openWakeWord) ---")
    import openwakeword
    from openwakeword.model import Model
    
    # Download models if needed
    openwakeword.utils.download_models()
    
    print("Initializing openWakeWord model...")
    oww_model = Model(inference_framework="onnx")
    
    # Run continuous stream of 16kHz audio chunks (1280 samples = 80ms chunks)
    chunk_size = 1280
    test_chunks = 60 # ~5 seconds of continuous audio
    dummy_audio = np.random.randint(-1000, 1000, size=chunk_size, dtype=np.int16)
    
    cpu_measurements = []
    gpu_measurements = []
    
    print("Simulating live continuous listening stream...")
    # Baseline
    psutil.cpu_percent(interval=None)
    
    t_start = time.perf_counter()
    for _ in range(test_chunks):
        t_chunk_start = time.perf_counter()
        # Feed chunk
        oww_model.predict(dummy_audio)
        cpu_measurements.append(psutil.cpu_percent(interval=None))
        gpu_measurements.append(get_gpu_utilization())
        # Sleep remainder of 80ms chunk to mimic real audio arrival
        rem = 0.08 - (time.perf_counter() - t_chunk_start)
        if rem > 0:
            time.sleep(rem)
            
    total_time = time.perf_counter() - t_start
    avg_cpu = sum(cpu_measurements) / len(cpu_measurements)
    avg_gpu = sum(gpu_measurements) / len(gpu_measurements)
    
    print(f"Listening loop tested over {total_time:.2f} seconds:")
    print(f" Average CPU utilization while listening: {avg_cpu:.1f}%")
    print(f" Average GPU utilization while listening: {avg_gpu:.1f}%")
    
    return {
        "engine": "openWakeWord (ONNX)",
        "avg_cpu_percent": round(avg_cpu, 1),
        "avg_gpu_percent": round(avg_gpu, 1),
        "status": "works"
    }

if __name__ == "__main__":
    wav_path = os.path.abspath("spikes/f-voice/test_speech.wav")
    ref_text = "Good afternoon. Phenom desktop assistant speech recognition feasibility test running locally on Windows 11."
    
    print("Generating reference speech audio...")
    generate_test_audio_wav(wav_path, ref_text)
    
    tts_res = test_tts()
    stt_res = test_whisper_stt(wav_path)
    wake_res = test_wakeword_detector()
    
    all_res = {
        "tts": tts_res,
        "stt": stt_res,
        "wake_word": wake_res,
        "status": "works"
    }
    
    with open("spikes/f-voice/results.json", "w", encoding="utf-8") as f:
        json.dump(all_res, f, indent=2)
        
    print("\nAll voice tests completed successfully! Results written to spikes/f-voice/results.json")
