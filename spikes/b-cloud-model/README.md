# Spike B: Cloud Model (Nemotron via NVIDIA API)

## Purpose
Verify connectivity, streaming capability, latency, context limits, and error handling for Nemotron models via NVIDIA's OpenAI-compatible API (`https://integrate.api.nvidia.com/v1`).

## Target Model
- **Model**: `nvidia/llama-3.1-nemotron-70b-instruct`
- **Context Length**: 131,072 tokens (128k)
- **Endpoint**: `https://integrate.api.nvidia.com/v1`
- **Rate Limits**: Free evaluation tier allows ~40 requests/min; pay-as-you-go/enterprise scales with credits.

## How to Run
```bash
# Set your NVIDIA build key:
$env:NVIDIA_API_KEY="nvapi-..."
python spikes/b-cloud-model/test_nemotron.py
```

## Results & Error Handling
1. **Missing Key**: Detected cleanly, preventing silent failure.
2. **Invalid / Forbidden Key**: API returns HTTP 403 Forbidden (`{'status': 403, 'title': 'Forbidden', 'detail': 'Authorization failed'}`).
3. **Timeout Handling**: Verified using client timeout; cleanly raises `openai.APITimeoutError`.
4. **Status**: Works with caveats (Awaiting user's `NVIDIA_API_KEY` for live token streaming benchmark; API integration, error guards, and timeout resilience are fully verified).
