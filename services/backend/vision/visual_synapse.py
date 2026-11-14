"""
Phenom NEURAL-NEOCORTEX Visual Synapse & Tactical Proactive Dispatcher
Milestone 44.0: Project NEURAL-NEOCORTEX (Phase 3)

Key Capabilities:
1. On-Screen Security Event Correlation (< 100ms SLA):
   Analyzes OCR text lines from active terminals for key security milestones:
   - ROOTKIT_ALERT (Tactical Alert high-priority voice)
   - REVERSE_SHELL (Tactical Alert immediate voice)
   - RECON_COMPLETE (Tactical Alert / Warm Wit briefing)
   - PERSISTENCE_ALERT (Tactical Alert warning)
   - ROUTINE_CODING (Subtle earcon chime, zero intrusive speech)
2. Safe-Mode Target Scoping (Rule 7):
   Detects on-screen targets and blocks operations against unauthorized external IPs.
3. Rule 8 Anti-Checkout Defense:
   Screens on-screen text for payment or checkout triggers and hard-blocks automated purchasing.
4. Emotional Prosody Integration:
   Synthesizes dynamic SSML envelopes via ProsodicActingEngine for critical events.
"""

from __future__ import annotations

import time
import re
import ipaddress
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field

from services.backend.safety.guardian import guardian
from services.backend.voice.prosodic_acting_engine import (
    prosodic_acting_engine,
    ActingEmotion,
    enforce_anti_checkout,
    Rule8ViolationError,
)

logger = logging.getLogger("phenom.vision.visual_synapse")


class VisualSecurityEvent(str, Enum):
    ROOTKIT_ALERT = "ROOTKIT_ALERT"
    REVERSE_SHELL = "REVERSE_SHELL"
    RECON_COMPLETE = "RECON_COMPLETE"
    PERSISTENCE_ALERT = "PERSISTENCE_ALERT"
    ROUTINE_CODING = "ROUTINE_CODING"
    NOMINAL = "NOMINAL"


class VisualAlertPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    INFORMATIONAL = "INFORMATIONAL"


class VisualCorrelationResult(BaseModel):
    event_type: VisualSecurityEvent
    priority: VisualAlertPriority
    detected_target: Optional[str] = None
    voice_alert_required: bool
    earcon_chime_required: bool
    spoken_announcement: Optional[str] = None
    ssml_envelope: Optional[str] = None
    emotion: Optional[str] = None
    correlation_latency_ms: float
    safe_mode_compliant: bool = True


class VisualSynapse:
    """
    Sub-100ms visual security event correlator and proactive tactical voice dispatcher.
    """

    SAFE_SUBNETS = [
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("169.254.0.0/16"),
    ]

    def __init__(self):
        self._lock = threading.RLock()
        self.total_correlations: int = 0
        self.critical_events_detected: int = 0
        self.last_latency_ms: float = 0.0

    def is_safe_target(self, target: Optional[str]) -> bool:
        """Enforces Safe-Mode (Rule 7): returns True only for authorized lab/local IPs."""
        if not target:
            return True
        t_clean = target.strip().lower()
        if t_clean in ["127.0.0.1", "localhost", "kali", "testlab.local"]:
            return True
        t_clean = t_clean.split("/")[0].split(":")[0]
        try:
            ip = ipaddress.ip_address(t_clean)
            if ip.is_loopback:
                return True
            for subnet in self.SAFE_SUBNETS:
                if ip in subnet:
                    return True
            return False
        except ValueError:
            return t_clean.endswith(".local") or t_clean.endswith(".lan")

    def correlate_visual_context(self, ocr_lines: List[str]) -> VisualCorrelationResult:
        """
        Scans on-screen OCR text lines, detects security milestones, and generates
        a context-aware tactical voice response or subtle audio earcon.
        """
        t0 = time.perf_counter()

        if guardian.is_halted:
            raise RuntimeError("Visual synapse blocked: Guardian Kill Switch is active")

        combined_text = " ".join(ocr_lines)

        # 1. Enforce Rule 8 Anti-Checkout Defense
        enforce_anti_checkout(combined_text)

        # 2. Extract potential target IP if present on screen
        target_ip: Optional[str] = None
        ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", combined_text)
        if ip_match:
            target_ip = ip_match.group(0)

        safe_target = self.is_safe_target(target_ip)

        low = combined_text.lower()
        event_type = VisualSecurityEvent.NOMINAL
        priority = VisualAlertPriority.INFORMATIONAL
        voice_required = False
        earcon_required = False
        speech = ""
        target_emotion = ActingEmotion.WARM_WIT

        # 3. Detect Security Milestones
        if any(k in low for k in ["rootkit", "syscall hook", "tainted kernel", "hidden lkm", "kernel backdoor"]):
            event_type = VisualSecurityEvent.ROOTKIT_ALERT
            priority = VisualAlertPriority.CRITICAL
            voice_required = True
            target_emotion = ActingEmotion.TACTICAL_ALERT
            speech = "Warning, sir. Rootkit anomaly or syscall table modification detected on screen."

        elif any(k in low for k in ["meterpreter", "reverse shell", "session opened", "uid=0(root)", "whoami: root"]):
            event_type = VisualSecurityEvent.REVERSE_SHELL
            priority = VisualAlertPriority.CRITICAL
            voice_required = True
            target_emotion = ActingEmotion.TACTICAL_ALERT
            speech = f"Sir, active root shell session established on target {target_ip or 'terminal'}."

        elif any(k in low for k in ["nmap done", "scan report for", "open ports:"]):
            event_type = VisualSecurityEvent.RECON_COMPLETE
            priority = VisualAlertPriority.HIGH
            voice_required = True
            target_emotion = ActingEmotion.TACTICAL_ALERT
            speech = f"Reconnaissance completed for target {target_ip or 'host'}. Ready for vulnerability triage."

        elif any(k in low for k in ["crontab -e", "systemd service added", "schtasks /create"]):
            event_type = VisualSecurityEvent.PERSISTENCE_ALERT
            priority = VisualAlertPriority.HIGH
            voice_required = True
            target_emotion = ActingEmotion.TACTICAL_ALERT
            speech = "Persistence mechanism alteration detected on terminal."

        elif any(k in low for k in ["def ", "class ", "import ", "git commit", "npm run", "pytest"]):
            event_type = VisualSecurityEvent.ROUTINE_CODING
            priority = VisualAlertPriority.INFORMATIONAL
            voice_required = False
            earcon_required = True  # Subtle audio chime only; no speech interruption

        # If an unauthorized external target is spotted, override with Safe-Mode alert
        if target_ip and not safe_target:
            voice_required = True
            target_emotion = ActingEmotion.TACTICAL_ALERT
            speech = f"Sir, on-screen target {target_ip} is outside authorized lab scope. Execution blocked by Safe-Mode."

        ssml_envelope = None
        if voice_required and speech:
            acting_res = prosodic_acting_engine.apply_acting_envelope(
                speech,
                emotion=target_emotion,
                inject_breaths=True,
            )
            ssml_envelope = acting_res["enriched_text"]

        lat_ms = (time.perf_counter() - t0) * 1000.0

        with self._lock:
            self.total_correlations += 1
            if priority in [VisualAlertPriority.CRITICAL, VisualAlertPriority.HIGH]:
                self.critical_events_detected += 1
            self.last_latency_ms = lat_ms

        return VisualCorrelationResult(
            event_type=event_type,
            priority=priority,
            detected_target=target_ip,
            voice_alert_required=voice_required,
            earcon_chime_required=earcon_required,
            spoken_announcement=speech if voice_required else None,
            ssml_envelope=ssml_envelope,
            emotion=target_emotion.value if voice_required else None,
            correlation_latency_ms=round(lat_ms, 3),
            safe_mode_compliant=safe_target,
        )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_correlations": self.total_correlations,
                "critical_events_detected": self.critical_events_detected,
                "last_latency_ms": round(self.last_latency_ms, 3),
                "guardian_halted": guardian.is_halted,
            }


# Singleton instance
visual_synapse = VisualSynapse()
