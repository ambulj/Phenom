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


export interface VoiceAmplitudePayload {
  amplitude: number;
}

export interface VoiceAmplitudeMsg extends BaseMessage {
  type: 'voice.amplitude';
  payload: VoiceAmplitudePayload;
}

export interface VoiceStatusPayload {
  enabled: boolean;
  muted: boolean;
}

export interface VoiceStatusMsg extends BaseMessage {
  type: 'voice.status';
  payload: VoiceStatusPayload;
}

export interface HotkeysResultPayload {
  success: boolean;
  error?: string | null;
  hotkeys: Record<string, string>;
}

export interface HotkeysResultMsg extends BaseMessage {
  type: 'hotkeys.result';
  payload: HotkeysResultPayload;
}

export interface VoiceTogglePayload {
  enabled: boolean;
}

export interface VoiceToggleMsg extends BaseMessage {
  type: 'voice.toggle';
  payload: VoiceTogglePayload;
}

export interface VoiceMutePayload {
  muted: boolean;
}

export interface VoiceMuteMsg extends BaseMessage {
  type: 'voice.mute';
  payload: VoiceMutePayload;
}

export interface HotkeysUpdatePayload {
  action: string;
  key_combo: string;
}

export interface HotkeysUpdateMsg extends BaseMessage {
  type: 'hotkeys.update';
  payload: HotkeysUpdatePayload;
}

export interface BrowserFramePayload {
  image_data: string;
}

export interface BrowserFrameMsg extends BaseMessage {
  type: 'browser.frame';
  payload: BrowserFramePayload;
}

export interface AutomationTakeoverPromptPayload {
  reason: string;
  session_id?: string | null;
  app_name?: string | null;
  timestamp?: string | null;
}

export interface AutomationTakeoverPromptMsg extends BaseMessage {
  type: 'automation.takeover_prompt';
  payload: AutomationTakeoverPromptPayload;
}

export interface AutomationTakeoverReplyPayload {
  decision: 'continue' | 'stop';
  session_id?: string | null;
}

export interface AutomationTakeoverReplyMsg extends BaseMessage {
  type: 'automation.takeover_reply';
  payload: AutomationTakeoverReplyPayload;
}

export interface MissionMorningDebriefPayload {
  summary: {
    date: string;
    total_missions: number;
    successful_missions: number;
    failed_missions: number;
    tests_fixed: number;
    lines_added: number;
    lines_deleted: number;
    touched_files: string[];
    missions: Array<{
      mission_id: string;
      title: string;
      status: 'pending' | 'running' | 'healing' | 'completed' | 'failed' | 'aborted' | 'halted';
      tests_passed: number;
      tests_fixed: number;
      lines_added: number;
      lines_deleted: number;
      files_changed: string[];
      branch_name: string;
      worktree_path: string;
      started_at: string;
      completed_at?: string;
      diagnostic_log: string;
    }>;
    executive_summary: string;
  };
  celebrate: boolean;
  timestamp: string;
}

export interface MissionMorningDebriefMsg extends BaseMessage {
  type: 'mission.morning_debrief';
  payload: MissionMorningDebriefPayload;
}

// Swarm Debate Protocol Payloads (Milestone 10.0 Phase 1)
export interface SwarmDebateEscalationPayload {
  debate_id: string;
  proposal_title: string;
  proposal_description: string;
  proposal_diff?: string | null;
  risk_tier: RiskTier;
  final_score: number;
  verdict: string;
  gating_reasons: string[];
  specialist_breakdown: Record<string, number>;
  turns_count: number;
  last_turn_critiques: Record<string, any>;
  timestamp: string;
}

export interface SwarmDebateEscalationMsg extends BaseMessage {
  type: 'swarm.debate.escalation';
  payload: SwarmDebateEscalationPayload;
}

export interface SwarmDebateDecisionPayload {
  debate_id: string;
  decision: 'approve' | 'reject';
  reason?: string;
}

export interface SwarmDebateDecisionMsg extends BaseMessage {
  type: 'swarm.debate.decision';
  payload: SwarmDebateDecisionPayload;
}

// Hierarchical Tree-of-Thought (ToT) Goal DAG Types (PLN-01)
export type DAGNodeStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'PRUNED'
  | 'ROLLED_BACK'
  | 'SKIPPED';

export type DAGBranchType = 'PRIMARY' | 'CONTINGENCY' | 'EXPLORATORY';

export interface DAGNodePayload {
  node_id: string;
  title: string;
  description: string;
  action_type: string;
  tool_name?: string;
  tool_args?: Record<string, any>;
  depends_on: string[];
  branch_id: string;
  tier: number;
  status: DAGNodeStatus;
  feasibility_score: number;
  estimated_duration_sec: number;
  is_checkpoint: boolean;
  retry_count: number;
  max_retries: number;
  error?: string;
}

export interface DAGBranchPayload {
  branch_id: string;
  name: string;
  branch_type: DAGBranchType;
  node_ids: string[];
  feasibility_score: number;
  estimated_duration_sec: number;
  risk_tier: number;
  is_active: boolean;
  pruned: boolean;
  prune_reason?: string;
}

export interface GoalDAGPayload {
  dag_id: string;
  goal_description: string;
  nodes: Record<string, DAGNodePayload>;
  branches: Record<string, DAGBranchPayload>;
  active_branch_id: string;
  status: string;
  overall_progress_pct: number;
  checkpoint_count?: number;
  reflection_count?: number;
}

export interface GoalDAGUpdateMsg extends BaseMessage {
  type: 'goal.dag_update';
  payload: GoalDAGPayload;
}

export interface GoalPruneBranchMsg extends BaseMessage {
  type: 'goal.prune_branch';
  payload: {
    dag_id: string;
    branch_id: string;
    reason?: string;
  };
}

export interface GoalAbortMsg extends BaseMessage {
  type: 'goal.abort';
  payload: {
    dag_id: string;
    reason?: string;
  };
}

export interface CameraStatusPayload {
  is_streaming: boolean;
  node_id?: string;
  device_name?: string;
  last_frame_ts?: number;
  resolution?: string;
  battery_level?: number;
  is_charging?: boolean;
  wifi_rssi?: number;
  frames_received: number;
  is_halted: boolean;
  thumbnail_base64?: string;
}

export interface CameraStatusMsg extends BaseMessage {
  type: 'sensory.camera_status';
  payload: CameraStatusPayload;
}

export interface CameraFramePreviewMsg extends BaseMessage {
  type: 'sensory.camera_preview';
  payload: {
    frame_id: string;
    node_id: string;
    timestamp: number;
    image_base64: string;
    width: number;
    height: number;
    battery_level?: number;
    wifi_rssi?: number;
  };
}

export interface MediaDropTransferPayload {
  transfer_id: string;
  filename: string;
  file_size: number;
  direction: 'incoming' | 'outgoing';
  source_node_id: string;
  target_node_id: string;
  destination: string;
  state: 'pending' | 'transferring' | 'completed' | 'failed' | 'aborted';
  progress: number;
  bytes_transferred: number;
  sha256_checksum: string;
  error_message?: string;
  started_at: number;
  completed_at?: number;
  saved_path?: string;
}

export interface MediaDropUpdateMsg extends BaseMessage {
  type: 'sensory.media_drop_update';
  payload: MediaDropTransferPayload;
}

export interface CameraStreamToggleMsg extends BaseMessage {
  type: 'sensory.camera_toggle';
  payload: {
    node_id?: string;
    enable: boolean;
  };
}

export interface MediaDropAbortMsg extends BaseMessage {
  type: 'sensory.media_drop_abort';
  payload: {
    transfer_id: string;
    reason?: string;
  };
}

export interface DreamEngineStatusPayload {
  is_running: boolean;
  phase: 'IDLE' | 'INGESTING_EPISODES' | 'REPLAYING_TRACES' | 'COMPACTING_GRAPH' | 'ABSTRACTING_SCHEMAS' | 'COMPLETED' | 'HALTED';
  last_cycle_at?: number | null;
  total_cycles_completed: number;
  total_schemas_formed: number;
  is_halted: boolean;
  latest_report?: {
    cycle_id: string;
    episodes_replayed: number;
    schemas_formed: number;
    edges_pruned: number;
    duplicate_nodes_merged: number;
    duration_ms: number;
    completed_at: number;
  } | null;
}

export interface DreamStatusMsg extends BaseMessage {
  type: 'dream.status';
  payload: DreamEngineStatusPayload;
}

export interface DreamTriggerCycleMsg extends BaseMessage {
  type: 'dream.trigger_cycle';
  payload: {
    force?: boolean;
    max_episodes?: number;
  };
}

export type InboundServerMessage =
  | ChatTokenMsg
  | ChatDoneMsg
  | StateChangeMsg
  | ToolRequestMsg
  | ConfirmRequestMsg
  | LogEntryMsg
  | RulesUpdatedMsg
  | VoiceAmplitudeMsg
  | VoiceStatusMsg
  | HotkeysResultMsg
  | BrowserFrameMsg
  | AutomationTakeoverPromptMsg
  | MissionMorningDebriefMsg
  | SwarmDebateEscalationMsg
  | GoalDAGUpdateMsg
  | CameraStatusMsg
  | CameraFramePreviewMsg
  | MediaDropUpdateMsg
  | DreamStatusMsg
  | ErrorMsg;

export type OutboundClientMessage =
  | ChatSendMsg
  | ChatCancelMsg
  | ConfirmReplyMsg
  | SettingsUpdateMsg
  | KillSwitchTriggerMsg
  | KillSwitchResumeMsg
  | ModeSetMsg
  | VoiceToggleMsg
  | VoiceMuteMsg
  | HotkeysUpdateMsg
  | AutomationTakeoverReplyMsg
  | SwarmDebateDecisionMsg
  | GoalPruneBranchMsg
  | GoalAbortMsg
  | CameraStreamToggleMsg
  | MediaDropAbortMsg
  | DreamTriggerCycleMsg;
