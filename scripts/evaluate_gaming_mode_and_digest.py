"""
Phenom Hardening Pass 2 - Task 7j Evaluation Benchmark
Evaluates Gaming Mode & Notification Digest:
1. Detection log triggering gaming mode on game executables and full-screen DirectX/Vulkan apps.
2. Strict exclusions verified for browsers, video players, presentations, and remote desktop.
3. Resource governance lifecycle (notification mute, scheduler pause, power plan, VRAM offload, Orb freeze).
4. Full restoration on game exit.
5. 'What Did I Miss' notification digest with zero OTP and financial leakage proof.
"""

import os
import sys
import re
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backend.automation.gaming_mode import GamingModeManager, KNOWN_GAME_PROCESSES, EXCLUDED_PROCESSES
from services.backend.automation.notification_digest import NotificationDigestManager
from services.backend.resource.vram_manager import vram_manager
from services.backend.scheduler.cron import background_scheduler

async def main():
    print("=" * 80)
    print("PHENOM HARDENING PASS 2 - TASK 7j GAMING MODE & NOTIFICATION DIGEST EVALUATION")
    print("=" * 80)

    mgr = GamingModeManager()
    digest_mgr = NotificationDigestManager()

    # --------------------------------------------------------------------------
    # 1. Detection of Known Game Executables
    # --------------------------------------------------------------------------
    print("\n[1] Testing Gaming Mode Trigger on Game Executables...")
    games = ["cs2.exe", "valorant.exe", "steam.exe", "cyberpunk2077.exe", "dota2.exe"]
    for g in games:
        is_gaming, detected, reason = mgr.detect_gaming_state(mock_foreground_proc=g)
        assert is_gaming is True, f"Failed on {g}"
        print(f"  - Detected Game: {g:<22} -> Gaming Mode: {is_gaming} | Reason: {reason}")
    print("  PASS: All tested game executables successfully triggered gaming mode.")

    # --------------------------------------------------------------------------
    # 2. Detection of Fullscreen 3D / DirectX Applications
    # --------------------------------------------------------------------------
    print("\n[2] Testing Fullscreen DirectX / Vulkan Application Detection...")
    is_gaming, detected, reason = mgr.detect_gaming_state(
        mock_foreground_proc="black_myth_wukong.exe",
        mock_is_fullscreen=True
    )
    assert is_gaming is True
    print(f"  - Detected App: {'black_myth_wukong.exe':<22} -> Gaming Mode: {is_gaming} | Reason: {reason}")
    print("  PASS: Fullscreen DirectX / 3D engine detected correctly.")

    # --------------------------------------------------------------------------
    # 3. Strict Exclusion Filters (Browsers, Video, PPT, RDP)
    # --------------------------------------------------------------------------
    print("\n[3] Testing Strict Exclusion Filters (Must NEVER Trigger Gaming Mode)...")
    exclusions = [
        ("chrome.exe", "Web Browser"),
        ("brave.exe", "Web Browser"),
        ("vlc.exe", "Media Player"),
        ("mpv.exe", "Media Player"),
        ("powerpnt.exe", "Presentation Slides"),
        ("mstsc.exe", "Remote Desktop Protocol"),
        ("vmware.exe", "Virtualization Workstation"),
        ("virtualbox.exe", "Virtual Machine Shell")
    ]
    for proc, desc in exclusions:
        is_gaming, detected, reason = mgr.detect_gaming_state(
            mock_foreground_proc=proc,
            mock_is_fullscreen=True
        )
        assert is_gaming is False, f"CRITICAL: Excluded process {proc} triggered gaming mode!"
        print(f"  - Fullscreen {desc:<25} ({proc:<16}) -> Gaming Mode: {is_gaming} | Filter: {reason}")
    print("  PASS: Browsers, media players, presentations, and remote desktop strictly excluded.")

    # --------------------------------------------------------------------------
    # 4. Resource Governance Lifecycle (Enter & Exit)
    # --------------------------------------------------------------------------
    print("\n[4] Testing Gaming Actions & Restoration Lifecycle...")
    enter_res = await mgr.enter_gaming_mode("cyberpunk2077.exe")
    print(f"  - Entered Gaming Mode: {enter_res['game']}")
    print(f"    * Notifications Muted: {enter_res['notifications_muted']}")
    print(f"    * Scheduler Paused: {enter_res['scheduler_paused']}")
    print(f"    * Power Plan: {enter_res['power_plan']}")
    print(f"    * VRAM Offload (<100MB): {enter_res['vram_offloaded']} MB")
    print(f"    * Three.js Orb LOD: {enter_res['orb_lod']} (0 particles, 0 fps)")

    assert enter_res["notifications_muted"] is True
    assert enter_res["scheduler_paused"] is True
    assert enter_res["vram_offloaded"] <= 100.0
    assert enter_res["orb_lod"] == "freeze"

    exit_res = await mgr.exit_gaming_mode()
    print(f"  - Exited Gaming Mode:")
    print(f"    * Notifications Restored: {not exit_res['notifications_muted']}")
    print(f"    * Scheduler Resumed: {not exit_res['scheduler_paused']}")
    print(f"    * Power Plan Restored: {exit_res['power_plan']}")
    print(f"    * Three.js Orb LOD Restored: {exit_res['orb_lod']}")

    assert exit_res["notifications_muted"] is False
    assert exit_res["scheduler_paused"] is False
    assert exit_res["power_plan"] == "balanced"
    assert exit_res["orb_lod"] in ["high", "medium", "low"]
    print("  PASS: Resource governance and restoration lifecycle verified.")

    # --------------------------------------------------------------------------
    # 5. 'What Did I Miss' Notification Digest (Zero Leakage Proof)
    # --------------------------------------------------------------------------
    print("\n[5] Testing 'What Did I Miss' Notification Digest (Zero Leakage Guarantee)...")
    digest_mgr.buffer_notification("Telegram", "Alex", "Hey mate, let's catch up later.")
    digest_mgr.buffer_notification("Google", "Google Verification", "Your Google verification code is 849201. Do not share.")
    digest_mgr.buffer_notification("Calendar", "Sprint Review", "Sprint retrospective in 15 mins.")
    digest_mgr.buffer_notification("HDFC Bank", "Account Alert", "INR 45,000 debited from account ending in xx8912 on 29-Oct.")
    digest_mgr.buffer_notification("System", "Windows Security", "Security updates downloaded and ready.")

    digest = digest_mgr.generate_spoken_digest()
    spoken_text = digest["spoken_text"]
    print(f"  - Buffered Missed Notifications: {digest['count']}")
    print(f"  - Spoken Transcript:")
    print(f"    \"{spoken_text}\"")

    # Strict Leakage Audit
    assert "849201" not in spoken_text, "CRITICAL: Leaked OTP code in spoken text!"
    assert "45,000" not in spoken_text, "CRITICAL: Leaked financial currency amount in spoken text!"
    assert "xx8912" not in spoken_text, "CRITICAL: Leaked account digits in spoken text!"
    assert "8912" not in spoken_text, "CRITICAL: Leaked account number in spoken text!"

    leaked_numbers = re.findall(r"\b\d{4,8}\b", spoken_text)
    assert len(leaked_numbers) == 0, f"Leaked 4-8 digit numbers: {leaked_numbers}"

    print(f"  - OTP Leak Check: PASS (0 code digits leaked)")
    print(f"  - Bank Account Leak Check: PASS (0 financial account digits leaked)")
    print(f"  PASS: Notification digest spoken format verified with ZERO secrets or private details leaked.")

    print("\n" + "=" * 80)
    print("ALL TASK 7j ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY (PASS)")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
