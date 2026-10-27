// AUTO-GENERATED FROM services/backend/schemas/protocol.py
// DO NOT EDIT MANUALLY. Run 'npm run generate-types' to regenerate.

export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'halted';
export type RiskTier = 0 | 1 | 2 | 3;
export type DecisionType = 'auto' | 'approved' | 'denied' | 'blocked' | 'timeout';

export interface BaseMessage {
  id: string;
  type: string;
  ts: string;
}

// Client to Server
export interface ChatSendPayload {
  prompt: string;
  context_files?: string[];
  privacy_override?: 'private' | 'shareable';
}

export interface ChatSendMsg extends BaseMessage {
  type: 'chat.send';
  payload: ChatSendPayload;
}

export interface ChatCancelPayload {}

export interface ChatCancelMsg extends BaseMessage {
  type: 'chat.cancel';
  payload: ChatCancelPayload;
}

export interface ConfirmReplyPayload {
  request_id: string;
  decision: 'approved' | 'denied';
  remember_choice?: boolean;
  folder_path?: string | null;
}

export interface ConfirmReplyMsg extends BaseMessage {
  type: 'confirm.reply';
  payload: ConfirmReplyPayload;
}

export interface SettingsUpdatePayload {
  settings: Record<string, any>;
}

export interface SettingsUpdateMsg extends BaseMessage {
  type: 'settings.update';
  payload: SettingsUpdatePayload;
}

export interface KillSwitchTriggerPayload {
  reason?: string;
}

export interface KillSwitchTriggerMsg extends BaseMessage {
  type: 'killswitch.trigger';
  payload: KillSwitchTriggerPayload;
}

export interface KillSwitchResumePayload {}

export interface KillSwitchResumeMsg extends BaseMessage {
  type: 'killswitch.resume';
  payload: KillSwitchResumePayload;
}

export interface ModeSetPayload {
  mode: 'work' | 'study' | 'chill';
}

export interface ModeSetMsg extends BaseMessage {
  type: 'mode.set';
  payload: ModeSetPayload;
}

// Server to Client
export interface ChatTokenPayload {
  token: string;
  index: number;
}

export interface ChatTokenMsg extends BaseMessage {
  type: 'chat.token';
  payload: ChatTokenPayload;
}

export interface ChatDonePayload {
  total_tokens: number;
  duration_s: number;
  tps: number;
  full_text?: string;
}

export interface ChatDoneMsg extends BaseMessage {
  type: 'chat.done';
  payload: ChatDonePayload;
}

export interface StateChangePayload {
  state: OrbState;
  detail?: string | null;
}

export interface StateChangeMsg extends BaseMessage {
  type: 'state.change';
  payload: StateChangePayload;
}

export interface ToolRequestPayload {
  tool: string;
  args: Record<string, any>;
  tier: RiskTier;
}

export interface ToolRequestMsg extends BaseMessage {
  type: 'tool.request';
  payload: ToolRequestPayload;
}

export interface ConfirmRequestPayload {
  request_id: string;
  tool: string;
  tier: RiskTier;
  preview: string;
  args: Record<string, any>;
  can_remember?: boolean;
  folder_path?: string | null;
  timeout_seconds?: number;
}

export interface ConfirmRequestMsg extends BaseMessage {
  type: 'confirm.request';
  payload: ConfirmRequestPayload;
}

export interface LogEntryPayload {
  log_id: string;
  timestamp: string;
  source: string;
  tool: string;
  tier: RiskTier;
  arguments_redacted: string;
  decision: DecisionType;
  result_status: string;
  error?: string | null;
  undo_token?: string | null;
}

export interface LogEntryMsg extends BaseMessage {
  type: 'log.entry';
  payload: LogEntryPayload;
}

export interface LearnedRuleItem {
  id: string;
  rule_text: string;
  created_at: string;
  enabled: boolean;
}

export interface RulesUpdatedPayload {
  rules: LearnedRuleItem[];
}

export interface RulesUpdatedMsg extends BaseMessage {
  type: 'rules.updated';
  payload: RulesUpdatedPayload;
}

export interface ErrorPayload {
  message: string;
  code?: string;
}

export interface ErrorMsg extends BaseMessage {
  type: 'error';
  payload: ErrorPayload;
}

export type InboundServerMessage =
  | ChatTokenMsg
  | ChatDoneMsg
  | StateChangeMsg
  | ToolRequestMsg
  | ConfirmRequestMsg
  | LogEntryMsg
  | RulesUpdatedMsg
  | ErrorMsg;

export type OutboundClientMessage =
  | ChatSendMsg
  | ChatCancelMsg
  | ConfirmReplyMsg
  | SettingsUpdateMsg
  | KillSwitchTriggerMsg
  | KillSwitchResumeMsg
  | ModeSetMsg;
