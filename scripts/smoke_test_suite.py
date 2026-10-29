"""
Phenom End-to-End Smoke Verification Suite
Executes all hardening benchmarks, integration probes, and subsystem audits in sequence.
Produces a comprehensive subsystem smoke report.
"""

import sys
import subprocess
import time
from typing import Dict, List, Tuple

BENCHMARKS = [
    ("Zero Secrets Scanner", ["python", "scripts/scan_secrets.py", "--all"]),
    ("Voice & Hindi/Hinglish Accuracy", ["python", "scripts/evaluate_voice.py"]),
    ("VRAM & Storage Governance", ["python", "scripts/evaluate_vram_and_storage.py"]),
    ("Privacy Router & Fallback Cascade", ["python", "scripts/evaluate_privacy_router.py"]),
    ("Telegram Workflow & Screenshot Redaction", ["python", "scripts/evaluate_telegram_workflow.py"]),
    ("Orb Particle LOD & UX Boundaries", ["python", "scripts/evaluate_orb_and_voice_ux.py"]),
    ("Coding Agent Safety & Process Kill", ["python", "scripts/evaluate_coding_agent_safety.py"]),
    ("Gaming Mode & Notification Digest", ["python", "scripts/evaluate_gaming_mode_and_digest.py"]),
    ("Usage Tracking & Reset Controls", ["python", "scripts/evaluate_providers_usage_and_reset.py"]),
    ("Confirmations & Safe Mode Engine", ["python", "scripts/evaluate_confirmations_and_safe_mode.py"]),
    ("Clean Machine & Watchdog E2E Tests", ["python", "-m", "pytest", "services/backend/tests/test_clean_machine_e2e.py", "-v"]),
]

def run_smoke_suite():
    print("=" * 80)
    print("PHENOM END-TO-END MANUAL SMOKE VERIFICATION SUITE")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]} on {sys.platform}")
    print("=" * 80)

    results: List[Tuple[str, str, float, str]] = []
    total_start = time.time()

    for name, cmd in BENCHMARKS:
        print(f"\n[RUNNING] {name}...")
        start = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        elapsed = time.time() - start
        
        status = "PASS" if res.returncode == 0 else "FAIL"
        results.append((name, status, elapsed, res.stdout))
        
        indicator = "[OK]" if res.returncode == 0 else "[FAIL]"
        print(f"{indicator} {name} finished in {elapsed:.2f}s (Exit code: {res.returncode})")
        if res.returncode != 0:
            print("--- Output excerpt ---")
            lines = res.stdout.strip().split("\n")
            for line in lines[-10:]:
                print(f"  {line}")
            print("----------------------")

    total_elapsed = time.time() - total_start
    print("\n" + "=" * 80)
    print("SMOKE VERIFICATION SUMMARY REPORT")
    print("=" * 80)
    
    passed_count = sum(1 for _, s, _, _ in results if s == "PASS")
    total_count = len(results)

    for name, status, elapsed, _ in results:
        badge = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"  {badge:<8} | {name:<45} | {elapsed:>6.2f}s")

    print("-" * 80)
    print(f"TOTAL: {passed_count}/{total_count} Subsystems Verified in {total_elapsed:.2f}s")
    print("=" * 80)

    if passed_count != total_count:
        sys.exit(1)

if __name__ == "__main__":
    run_smoke_suite()
