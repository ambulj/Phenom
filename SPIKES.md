# SPIKES.md: Phase 0 results

For each spike: status (works / works with caveats / does not work), versions, measured numbers, what you would change.

| Spike | Status | Key numbers | Notes |
| --- | --- | --- | --- |
| A Local model | | first-token ms, tokens/s, VRAM, valid-JSON /20 | |
| B Cloud model | | latency, streaming, rate limit, context | |
| C Orb | | fps, GPU idle % | |
| D Backend link | | token latency, cancel ms | |
| E Encryption | | key roundtrip, unreadable without key | |
| F Voice | | CPU/GPU while listening, STT latency | |

## Recommendation
(stack changes, quantization to use, order of risk for Phases 1 and 2)
