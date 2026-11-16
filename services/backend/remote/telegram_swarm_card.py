"""Dynamic Editable Telegram Swarm Card Generator (Phase 48-05, TELE-03).

Formats real-time multi-agent swarm status cards with ASCII quorum indicators,
GPU VRAM gauges, agent assignment summaries, and emergency halt triggers.
"""

from typing import Any, Dict, List, Optional
import time


class TelegramSwarmCard:
    """Generates markdown status cards for the authorized Telegram mobile companion."""

    @staticmethod
    def generate_vram_gauge(used_mb: float, max_mb: float = 5632.0, width: int = 10) -> str:
        """Constructs an ASCII gauge for GPU VRAM utilization."""
        if max_mb <= 0:
            return "[░░░░░░░░░░] 0.0 GB"
        ratio = min(1.0, max(0.0, used_mb / max_mb))
        fill_count = int(round(ratio * width))
        empty_count = width - fill_count
        bar = "█" * fill_count + "░" * empty_count
        used_gb = used_mb / 1024.0
        max_gb = max_mb / 1024.0
        return f"[{bar}] {used_gb:.1f}/{max_gb:.1f} GB ({int(ratio * 100)}%)"

    @staticmethod
    def generate_quorum_indicator(
        coder_signed: bool,
        security_signed: bool,
        architect_arbitrated: bool = False,
        state: str = "quorum_reached",
    ) -> str:
        """Constructs ASCII indicator for two-tier quorum consensus status."""
        coder_icon = "✅" if coder_signed else "⏳"
        sec_icon = "✅" if security_signed else ("🛑" if state == "vetoed" else "⏳")
        arch_icon = "⚖️" if architect_arbitrated else "👁️"

        if state == "vetoed":
            return f"[CODER: {coder_icon}] [SECURITY: 🛑 VETOED] [ARCHITECT: ⚠️]"
        elif state == "quorum_reached":
            return f"[CODER: {coder_icon}] [SECURITY: {sec_icon}] [QUORUM: PASS]"
        elif state == "deadlocked":
            return f"[CODER: {coder_icon}] [SECURITY: ⚠️] [ARCHITECT: ⚖️ ARBITRATING]"
        else:
            return f"[CODER: {coder_icon}] [SECURITY: {sec_icon}] [PENDING]"

    @classmethod
    def format_swarm_card(
        cls,
        mission_id: str,
        active_role: str,
        current_task_title: str,
        quorum_state: str,
        coder_signed: bool,
        security_signed: bool,
        architect_arbitrated: bool = False,
        vram_mb: float = 4850.0,
        max_vram_mb: float = 5632.0,
        elapsed_seconds: float = 0.0,
        error: Optional[str] = None,
    ) -> str:
        """Format the complete Markdown message payload for Telegram companion."""
        vram_gauge = cls.generate_vram_gauge(vram_mb, max_vram_mb)
        quorum_meter = cls.generate_quorum_indicator(
            coder_signed=coder_signed,
            security_signed=security_signed,
            architect_arbitrated=architect_arbitrated,
            state=quorum_state,
        )

        mins = int(elapsed_seconds // 60)
        secs = int(elapsed_seconds % 60)
        timer_str = f"{mins:02d}:{secs:02d}"

        role_emoji = {
            "architect": "🏛️ ARCHITECT",
            "coder": "💻 CODER",
            "security_auditor": "🛡️ SECURITY AUDITOR",
            "web_scout": "🌐 WEB SCOUT",
        }.get(active_role.lower(), f"🤖 {active_role.upper()}")

        lines = [
            "⚡ *PHENOM MULTI-AGENT SWARM*",
            f"🎯 *Mission ID:* `{mission_id}`",
            f"👤 *Active Role:* `{role_emoji}`",
            f"📍 *Current Task:* _{current_task_title}_",
            f"🤝 *Consensus Quorum:* `{quorum_meter}`",
            f"📼 *RTX 3050 VRAM:* `{vram_gauge}`",
            f"⏱️ *Elapsed Time:* `{timer_str}`",
        ]

        if error:
            lines.append(f"⚠️ *Alert:* `{error}`")

        lines.extend([
            "",
            "⚙️ *Controls:* `/approve` to authorize patch • `/halt` to trigger Guardian kill switch",
        ])

        return "\n".join(lines)
