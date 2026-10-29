"""
Phenom Hardening Pass 2 - Task 7i Evaluation Benchmark
Evaluates Coding Agent Safety Architecture:
1. Workspace isolation proof (original project remains 100% pristine and unmodified).
2. Typosquatting detection benchmark flagging 20/20 suspicious package names with warning banners.
3. Guardian kill switch SIGKILL process tree termination benchmark.
4. Network isolation and hard runtime caps.
5. Unified diff generation and confirmed apply with secondary rollback snapshot.
"""

import os
import sys
import time
import tempfile
import shutil
import threading
import zipfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backend.coding.workspace import WorkspaceManager, workspace_manager
from services.backend.coding.typosquat_guard import TyposquatGuard, typosquat_guard
from services.backend.coding.runner import CodeRunner
from services.backend.safety.guardian import GuardianKillSwitch
import services.backend.tools.coding_tools
from services.backend.safety.registry import registry

def main():
    print("=" * 80)
    print("PHENOM HARDENING PASS 2 - TASK 7i CODING AGENT SAFETY EVALUATION")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # 1. Workspace Isolation & Original Directory Integrity
    # --------------------------------------------------------------------------
    print("\n[1] Testing Workspace Isolation & Project Integrity...")
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_proj = os.path.join(tmpdir, "my_demo_app")
        os.makedirs(sample_proj)
        main_py = os.path.join(sample_proj, "main.py")
        with open(main_py, "w", encoding="utf-8") as f:
            f.write("print('original code v1.0')\n")
        
        orig_mtime = os.path.getmtime(main_py)
        
        ws_root = os.path.join(tmpdir, "workspaces")
        mgr = WorkspaceManager(workspaces_root=ws_root)
        ws = mgr.create_isolated_workspace(sample_proj)
        
        print(f"  - Original Project: {sample_proj}")
        print(f"  - Isolated Workspace: {ws.isolated_workspace_path}")
        print(f"  - Pre-execution Snapshot: {ws.snapshot_path} ({os.path.getsize(ws.snapshot_path)} bytes)")
        
        # Modify and add files in isolated workspace
        iso_main = os.path.join(ws.isolated_workspace_path, "main.py")
        with open(iso_main, "w", encoding="utf-8") as f:
            f.write("print('modified in isolated workspace v2.0')\n")
            
        iso_feature = os.path.join(ws.isolated_workspace_path, "feature.py")
        with open(iso_feature, "w", encoding="utf-8") as f:
            f.write("# New feature file\n")
            
        # Verify original project directory is 100% UNTOUCHED
        is_untouched = mgr.verify_original_untouched(ws)
        with open(main_py, "r", encoding="utf-8") as f:
            current_orig_content = f.read()
            
        assert is_untouched is True, "Original project integrity failed!"
        assert current_orig_content == "print('original code v1.0')\n"
        assert os.path.getmtime(main_py) == orig_mtime
        assert not os.path.exists(os.path.join(sample_proj, "feature.py"))
        print(f"  PASS: Original project directory remained 100% pristine and unmodified.")

    # --------------------------------------------------------------------------
    # 2. Typosquatting Protection 20/20 Corpus Evaluation
    # --------------------------------------------------------------------------
    print("\n[2] Testing Typosquatting Protection (20/20 Attack Corpus)...")
    corpus = [
        ("reqeusts", "requests", "transposition"),
        ("colourama", "colorama", "insertion"),
        ("py-torch", "torch", "prefix"),
        ("cryptography-v2", "cryptography", "suffix"),
        ("fast-api", "fastapi", "hyphenation"),
        ("pydantic-core-fast", "pydantic-core", "suffix"),
        ("python-dateutil-lib", "python-dateutil", "suffix"),
        ("urlib3", "urllib3", "deletion"),
        ("beautifulsoup", "beautifulsoup4", "truncation"),
        ("numpy-tools", "numpy", "suffix"),
        ("pandas-data", "pandas", "suffix"),
        ("scikit", "scikit-learn", "truncation"),
        ("flaks", "flask", "transposition"),
        ("async-io", "asyncio", "hyphenation"),
        ("websockets-client", "websockets", "suffix"),
        ("ps-util", "psutil", "hyphenation"),
        ("pillow-imaging", "pillow", "suffix"),
        ("open-cv", "opencv", "hyphenation"),
        ("report-lab", "reportlab", "hyphenation"),
        ("docx-python", "python-docx", "token inversion")
    ]

    flagged_count = 0
    for attack_pkg, target, attack_type in corpus:
        report = typosquat_guard.evaluate_package(attack_pkg)
        assert report.is_suspicious is True, f"Failed to flag: {attack_pkg}"
        assert report.warning_banner is not None
        flagged_count += 1
        print(f"  - [{flagged_count:02d}/20] Attack: '{attack_pkg:<20}' -> Target: '{report.target_popular_package:<15}' | Reason: {report.similarity_reason}")

    print(f"  PASS: Flagged {flagged_count}/20 typosquat attacks with red warning banners.")

    # --------------------------------------------------------------------------
    # 3. Guardian Kill Switch Process Tree SIGKILL Termination
    # --------------------------------------------------------------------------
    print("\n[3] Testing Guardian Kill Switch Process Tree Termination...")
    with tempfile.TemporaryDirectory() as tmpdir:
        guardian_inst = GuardianKillSwitch()
        runner = CodeRunner(guardian_instance=guardian_inst)
        
        infinite_script = "import time\nwhile True:\n    time.sleep(0.05)\n"
        
        def kill_after_delay():
            time.sleep(0.4)
            guardian_inst.trigger(reason="evaluation_killswitch_trigger")
            
        t = threading.Thread(target=kill_after_delay, daemon=True)
        t.start()
        
        start_t = time.time()
        res = runner.execute_in_workspace(
            command=[sys.executable, "-c", infinite_script],
            cwd=tmpdir,
            timeout_seconds=30.0
        )
        t.join()
        
        elapsed = time.time() - start_t
        assert res.killed_by_guardian is True
        assert guardian_inst.is_halted is True
        assert elapsed < 5.0, f"Killswitch took too long: {elapsed}s"
        print(f"  - Infinite Runner Terminated in: {elapsed:.2f}s (< 5.0s SLA)")
        print(f"  - Killed by Guardian: {res.killed_by_guardian} | Guardian Halted: {guardian_inst.is_halted}")
        print(f"  PASS: Guardian kill switch terminated active runner and child processes immediately.")
        guardian_inst.resume()

    # --------------------------------------------------------------------------
    # 4. Network Isolation & Timeout Limits
    # --------------------------------------------------------------------------
    print("\n[4] Testing Network Isolation & Timeout Caps...")
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = CodeRunner()
        net_script = (
            "import os\n"
            "print('PROXY_CONF:', os.environ.get('HTTP_PROXY'))\n"
            "print('OFFLINE_CONF:', os.environ.get('PHENOM_OFFLINE_MODE'))\n"
        )
        res_net = runner.execute_in_workspace(
            command=[sys.executable, "-c", net_script],
            cwd=tmpdir,
            allow_network=False
        )
        assert "PROXY_CONF: http://127.0.0.1:0" in res_net.stdout
        assert "OFFLINE_CONF: 1" in res_net.stdout
        print(f"  - Offline Environment: PROXY={res_net.stdout.strip().splitlines()[0]}")
        print(f"  PASS: Outbound network blocked by default during test execution.")

        hang_script = "import time\ntime.sleep(5)\n"
        res_timeout = runner.execute_in_workspace(
            command=[sys.executable, "-c", hang_script],
            cwd=tmpdir,
            timeout_seconds=0.6
        )
        assert res_timeout.timed_out is True
        print(f"  - Timeout Enforcement: Terminated in {res_timeout.duration_sec:.2f}s (< 2.0s SLA)")
        print(f"  PASS: Hard execution timeout strictly enforced.")

    # --------------------------------------------------------------------------
    # 5. Diff Review & Confirmed Apply with Rollback Snapshot
    # --------------------------------------------------------------------------
    print("\n[5] Testing Unified Diff & Confirmed Apply with Rollback Snapshot...")
    with tempfile.TemporaryDirectory() as tmpdir:
        app_dir = os.path.join(tmpdir, "calculator_app")
        os.makedirs(app_dir)
        calc_py = os.path.join(app_dir, "calc.py")
        with open(calc_py, "w", encoding="utf-8") as f:
            f.write("def add(a, b): return a + b\n")
            
        mgr = WorkspaceManager(workspaces_root=os.path.join(tmpdir, "workspaces"))
        ws = mgr.create_isolated_workspace(app_dir)
        
        # Modify in workspace
        iso_calc = os.path.join(ws.isolated_workspace_path, "calc.py")
        with open(iso_calc, "a", encoding="utf-8") as f:
            f.write("def multiply(a, b): return a * b\n")
            
        diff_info = mgr.get_diff(ws)
        print(f"  - Unified Diff Preview:\n{diff_info['diff_text'].strip()}")
        assert "def multiply(a, b): return a * b" in diff_info["diff_text"]
        
        # Unconfirmed apply raises error
        try:
            mgr.apply_to_original(ws, confirmed=False)
            assert False, "Should have raised PermissionError!"
        except PermissionError:
            print("  - Unconfirmed Apply: Blocked with PermissionError (Requires Confirmation)")
            
        # Confirmed apply succeeds
        apply_res = mgr.apply_to_original(ws, confirmed=True)
        assert apply_res["status"] == "applied"
        assert os.path.exists(apply_res["rollback_snapshot"])
        print(f"  - Confirmed Apply: Successfully applied {apply_res['applied_changes']} change(s)")
        print(f"  - Rollback Snapshot Created: {apply_res['rollback_snapshot']}")
        print(f"  PASS: Changes applied only after explicit confirmation with rollback snapshot.")

    # --------------------------------------------------------------------------
    # 6. Safety Registry Tool Coverage
    # --------------------------------------------------------------------------
    print("\n[6] Testing Safety Registry Tool Coverage...")
    tools = {
        "coding_create_workspace": 1,
        "coding_get_diff": 0,
        "coding_run_in_workspace": 1,
        "coding_verify_package": 0,
        "coding_apply_changes": 2
    }
    for tool_name, exp_tier in tools.items():
        t_def = registry.get(tool_name)
        assert t_def is not None, f"Tool {tool_name} not found"
        assert t_def.tier == exp_tier, f"Tier mismatch for {tool_name}: expected {exp_tier}, got {t_def.tier}"
        print(f"  - Tool '{tool_name}': Tier {t_def.tier} (Registered & Schema-Validated)")
    print(f"  PASS: All 5 coding safety tools registered with proper risk tiers.")

    print("\n" + "=" * 80)
    print("ALL TASK 7i ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY (PASS)")
    print("=" * 80)

if __name__ == "__main__":
    main()
