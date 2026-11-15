"""
Phenom Specialist Model Setup & Verification Script (Task 6D)
Resolves 'hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M' by name,
verifies its existence in Ollama, records its file digest and size in a manifest,
and fails loudly on any unknown or non-resolving model name without silent substitution.
"""

import sys
import json
import os
import argparse
from datetime import datetime, timezone
import httpx

DEFAULT_SPECIALIST_MODEL = "hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M"
MANIFEST_PATH = os.path.abspath("reports/specialist_model_manifest.json")
OLLAMA_API_BASE = "http://localhost:11434"

def acquire_and_verify_specialist_model(model_name: str = DEFAULT_SPECIALIST_MODEL, pull_if_missing: bool = False) -> dict:
    """
    Resolves the specialist model in Ollama by exact name.
    If the model fails to resolve, stops with a clear error naming exactly what was attempted.
    Never silently substitutes a different model.
    """
    print(f"[*] Attempting to resolve specialist model: '{model_name}'...")
    
    # 1. Query Ollama /api/tags
    try:
        resp = httpx.get(f"{OLLAMA_API_BASE}/api/tags", timeout=15.0)
    except Exception as e:
        err = f"CRITICAL: Failed to connect to Ollama runtime at {OLLAMA_API_BASE}: {e}"
        print(f"[!] {err}")
        raise RuntimeError(err)
        
    if resp.status_code != 200:
        err = f"CRITICAL: Ollama returned status {resp.status_code} when querying model tags."
        print(f"[!] {err}")
        raise RuntimeError(err)
        
    tags_data = resp.json()
    available_models = tags_data.get("models", [])
    
    # Find matching model
    found_model = None
    for m in available_models:
        name = m.get("name", "")
        if name == model_name or (":" in model_name and name.startswith(model_name)):
            found_model = m
            break
            
    if not found_model:
        # Check if pull requested
        if pull_if_missing:
            print(f"[*] Model '{model_name}' not in local cache. Attempting pull...")
            try:
                pull_resp = httpx.post(f"{OLLAMA_API_BASE}/api/pull", json={"name": model_name, "stream": False}, timeout=600.0)
                if pull_resp.status_code != 200:
                    err = (
                        f"CRITICAL: Failed to resolve specialist model '{model_name}'. "
                        f"Ollama pull returned HTTP {pull_resp.status_code}: {pull_resp.text}. "
                        f"Phenom will NOT silently substitute a different model."
                    )
                    print(f"[!] {err}")
                    raise RuntimeError(err)
                # Re-verify tags
                tags_data = httpx.get(f"{OLLAMA_API_BASE}/api/tags", timeout=15.0).json()
                for m in tags_data.get("models", []):
                    if m.get("name", "") == model_name:
                        found_model = m
                        break
            except Exception as pe:
                err = (
                    f"CRITICAL: Failed to resolve specialist model '{model_name}'. "
                    f"Network or pull error: {pe}. "
                    f"Phenom will NOT silently substitute a different model."
                )
                print(f"[!] {err}")
                raise RuntimeError(err)

    if not found_model:
        err = (
            f"CRITICAL: Specialist model '{model_name}' failed to resolve in Ollama. "
            f"The named repo/quantization does not exist or is not available. "
            f"Available models: {[m.get('name') for m in available_models]}. "
            f"Phenom will NOT silently substitute a different model."
        )
        print(f"[!] {err}")
        raise RuntimeError(err)
        
    digest = found_model.get("digest", "")
    size = found_model.get("size", 0)
    details = found_model.get("details", {})
    
    # 2. Inspect /api/show for parameter details
    try:
        show_resp = httpx.post(f"{OLLAMA_API_BASE}/api/show", json={"name": model_name}, timeout=15.0)
        if show_resp.status_code == 200:
            show_data = show_resp.json()
            if "details" in show_data:
                details.update(show_data["details"])
    except Exception:
        pass
        
    manifest = {
        "model_name": model_name,
        "digest": digest,
        "size_bytes": size,
        "size_gb": round(size / (1024**3), 2),
        "details": details,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "status": "VERIFIED_SPECIALIST_READY"
    }
    
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"[+] Specialist model '{model_name}' successfully resolved and verified!")
    print(f"    - Digest / Hash: {digest}")
    print(f"    - Size: {size} bytes ({manifest['size_gb']} GB)")
    print(f"    - Recorded in manifest: {MANIFEST_PATH}")
    return manifest

def main():
    parser = argparse.ArgumentParser(description="Setup and verify specialist security model.")
    parser.add_argument("--model", default=DEFAULT_SPECIALIST_MODEL, help="Model name/tag")
    parser.add_argument("--pull", action="store_true", help="Pull model if missing")
    parser.add_argument("--verify-fail-test", action="store_true", help="Test intentional failure on invalid model name")
    args = parser.parse_args()
    
    if args.verify_fail_test:
        test_bad_name = "hf.co/nonexistent-org/Definitely-Fake-Exploit-Model-GGUF:Q4_K_M"
        print(f"[*] Running deliberate failure test with invalid model name: '{test_bad_name}'")
        try:
            acquire_and_verify_specialist_model(test_bad_name, pull_if_missing=False)
            print("[!] ERROR: Verification unexpectedly passed for fake model!")
            sys.exit(1)
        except RuntimeError as re:
            print(f"[+] SUCCESS: Deliberate failure caught as expected: {re}")
            sys.exit(0)
            
    try:
        acquire_and_verify_specialist_model(args.model, pull_if_missing=args.pull)
        sys.exit(0)
    except Exception as e:
        print(f"[!] SETUP FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
