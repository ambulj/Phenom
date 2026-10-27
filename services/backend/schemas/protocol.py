"""
Phenom WebSocket Protocol Models
Strictly typed Pydantic V2 schemas for client-server communication.
Every message has `id`, `type`, and `ts` (ISO timestamp).
"""

from typing import Literal, Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field

OrbState = Literal["idle", "listening", "thinking", "speaking", "halted"]
RiskTier = Literal[0, 1, 2, 3]
DecisionType = Literal["auto", "approved", "denied", "blocked", "timeout"]

def current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()

def generate_id() -> str:
    return str(uuid.uuid4())

# Base Message Schema
class BaseMessage(BaseModel):
    id: str = Field(default_factory=generate_id)
    type: str
    ts: str = Field(default_factory=current_iso_time)

# ==========================================
# Client to Server Payloads
# ==========================================

class ChatSendPayload(BaseModel):
    prompt: str
    context_files: List[str] = Field(default_factory=list)
    privacy_override: Optional[Literal["private", "shareable"]] = None

class ChatSendMsg(BaseMessage):
    type: Literal["chat.send"] = "chat.send"
    payload: ChatSendPayload

class ChatCancelPayload(BaseModel):
    pass

class ChatCancelMsg(BaseMessage):
    type: Literal["chat.cancel"] = "chat.cancel"
    payload: ChatCancelPayload = Field(default_factory=ChatCancelPayload)

class ConfirmReplyPayload(BaseModel):
    request_id: str
    decision: Literal["approved", "denied"]
    remember_choice: bool = False
    folder_path: Optional[str] = None

class ConfirmReplyMsg(BaseMessage):
    type: Literal["confirm.reply"] = "confirm.reply"
    payload: ConfirmReplyPayload

class SettingsUpdatePayload(BaseModel):
    settings: Dict[str, Any]

class SettingsUpdateMsg(BaseMessage):
    type: Literal["settings.update"] = "settings.update"
    payload: SettingsUpdatePayload

class KillSwitchTriggerPayload(BaseModel):
    reason: str = "user_triggered"

class KillSwitchTriggerMsg(BaseMessage):
    type: Literal["killswitch.trigger"] = "killswitch.trigger"
    payload: KillSwitchTriggerPayload = Field(default_factory=KillSwitchTriggerPayload)

class KillSwitchResumePayload(BaseModel):
    pass

class KillSwitchResumeMsg(BaseMessage):
    type: Literal["killswitch.resume"] = "killswitch.resume"
    payload: KillSwitchResumePayload = Field(default_factory=KillSwitchResumePayload)

class ModeSetPayload(BaseModel):
    mode: Literal["work", "study", "chill"]

class ModeSetMsg(BaseMessage):
    type: Literal["mode.set"] = "mode.set"
    payload: ModeSetPayload

# ==========================================
# Server to Client Payloads
# ==========================================

class ChatTokenPayload(BaseModel):
    token: str
    index: int

class ChatTokenMsg(BaseMessage):
    type: Literal["chat.token"] = "chat.token"
    payload: ChatTokenPayload

class ChatDonePayload(BaseModel):
    total_tokens: int
    duration_s: float
    tps: float
    full_text: Optional[str] = None

class ChatDoneMsg(BaseMessage):
    type: Literal["chat.done"] = "chat.done"
    payload: ChatDonePayload

class StateChangePayload(BaseModel):
    state: OrbState
    detail: Optional[str] = None

class StateChangeMsg(BaseMessage):
    type: Literal["state.change"] = "state.change"
    payload: StateChangePayload

class ToolRequestPayload(BaseModel):
    tool: str
    args: Dict[str, Any]
    tier: RiskTier

class ToolRequestMsg(BaseMessage):
    type: Literal["tool.request"] = "tool.request"
    payload: ToolRequestPayload

class ConfirmRequestPayload(BaseModel):
    request_id: str
    tool: str
    tier: RiskTier
    preview: str
    args: Dict[str, Any]
    can_remember: bool = False
    folder_path: Optional[str] = None
    timeout_seconds: int = 120

class ConfirmRequestMsg(BaseMessage):
    type: Literal["confirm.request"] = "confirm.request"
    payload: ConfirmRequestPayload

class LogEntryPayload(BaseModel):
    log_id: str
    timestamp: str
    source: str
    tool: str
    tier: RiskTier
    arguments_redacted: str
    decision: DecisionType
    result_status: str
    error: Optional[str] = None
    undo_token: Optional[str] = None

class LogEntryMsg(BaseMessage):
    type: Literal["log.entry"] = "log.entry"
    payload: LogEntryPayload

class LearnedRuleItem(BaseModel):
    id: str
    rule_text: str
    created_at: str
    enabled: bool = True

class RulesUpdatedPayload(BaseModel):
    rules: List[LearnedRuleItem]

class RulesUpdatedMsg(BaseMessage):
    type: Literal["rules.updated"] = "rules.updated"
    payload: RulesUpdatedPayload

class ErrorPayload(BaseModel):
    message: str
    code: str = "ERROR"

class ErrorMsg(BaseMessage):
    type: Literal["error"] = "error"
    payload: ErrorPayload

# ==========================================
# Voice Protocol Payloads (Phase 2)
# ==========================================

class VoiceAmplitudePayload(BaseModel):
    amplitude: float

class VoiceAmplitudeMsg(BaseMessage):
    type: Literal["voice.amplitude"] = "voice.amplitude"
    payload: VoiceAmplitudePayload

class VoiceStatusPayload(BaseModel):
    enabled: bool
    muted: bool

class VoiceStatusMsg(BaseMessage):
    type: Literal["voice.status"] = "voice.status"
    payload: VoiceStatusPayload

class VoiceTogglePayload(BaseModel):
    enabled: bool

class VoiceToggleMsg(BaseMessage):
    type: Literal["voice.toggle"] = "voice.toggle"
    payload: VoiceTogglePayload

class VoiceMutePayload(BaseModel):
    muted: bool

class VoiceMuteMsg(BaseMessage):
    type: Literal["voice.mute"] = "voice.mute"
    payload: VoiceMutePayload

class HotkeysUpdatePayload(BaseModel):
    action: str
    key_combo: str

class HotkeysUpdateMsg(BaseMessage):
    type: Literal["hotkeys.update"] = "hotkeys.update"
    payload: HotkeysUpdatePayload

# ==========================================
# Automation Protocol Payloads (Phase 3)
# ==========================================

class BrowserFramePayload(BaseModel):
    image_data: str

class BrowserFrameMsg(BaseMessage):
    type: Literal["browser.frame"] = "browser.frame"
    payload: BrowserFramePayload

class AutomationTakeoverPromptPayload(BaseModel):
    reason: str

class AutomationTakeoverPromptMsg(BaseMessage):
    type: Literal["automation.takeover_prompt"] = "automation.takeover_prompt"
    payload: AutomationTakeoverPromptPayload

class AutomationTakeoverReplyPayload(BaseModel):
    decision: Literal["continue", "stop"]

class AutomationTakeoverReplyMsg(BaseMessage):
    type: Literal["automation.takeover_reply"] = "automation.takeover_reply"
    payload: AutomationTakeoverReplyPayload


