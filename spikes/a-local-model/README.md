# Spike A: Local Model Feasibility & Quantization Benchmark

## Purpose
Evaluate local 8B instruct model performance on this machine's NVIDIA GPU across 4-bit and 8-bit quantizations, measuring first-token latency, tokens per second, VRAM use, tool-calling / JSON validity over 20 sample prompts, and a 3,000-word document summary.

## Hardware Environment
- **GPU**: NVIDIA GeForce RTX 3050 Laptop GPU (6,144 MB VRAM)
- **Driver**: 581.86, CUDA 13.0
- **Runner**: Ollama v0.40.11 (llama.cpp backend with CUDA)

## Benchmarked Models
1. **4-bit**: `llama3:latest` (8.0B parameters, Q4_0, 4.7 GB)
2. **8-bit**: `llama3:8b-instruct-q8_0` (8.0B parameters, Q8_0, 8.5 GB)

## How to Run
```bash
# 4-bit benchmark:
python spikes/a-local-model/benchmark.py llama3:latest

# 8-bit benchmark:
python spikes/a-local-model/benchmark.py llama3:8b-instruct-q8_0
```

## Comparative Results
| Metric | 4-bit (`llama3:latest`) | 8-bit (`llama3:8b-instruct-q8_0`) |
|---|---|---|
| **GPU/CPU Offload** | 78% GPU / 22% CPU | 45% GPU / 55% CPU |
| **Peak VRAM Used** | 5,652 MB | 5,532 MB (spills to host RAM) |
| **First-Token Latency (median)** | **2,175.5 ms** | **2,274.4 ms** |
| **Throughput (median)** | **14.85 tps** | **5.63 tps** (2.6x slower) |
| **Tool-Calling Reliability** | **20 / 20 (100%)** | **20 / 20 (100%)** |
| **JSON Schema Compliance** | **20 / 20 (100%)** | **20 / 20 (100%)** |
| **3,000-word Summary Time** | **24.87 s** (13.2 tps) | **63.99 s** (4.3 tps) |

## Recommendation
Use **4-bit quantization (Q4_0 or Q4_K_M)** for all subsequent phases. 8-bit causes a severe PCIe transfer bottleneck due to the 6GB VRAM constraint, dropping speed below the threshold for interactive voice/Jarvis responses (5.6 tps vs 14.9 tps).
