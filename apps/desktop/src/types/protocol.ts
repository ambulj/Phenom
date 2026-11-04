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

export interface WindowRectPayload {
  left: number;
  top: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
}

export interface ActiveWindowTargetPayload {
  hwnd: number;
  title: string;
  process_name: string;
  pid: number;
  bounds: WindowRectPayload;
  is_minimized: boolean;
  is_focused: boolean;
  captured_at: number;
}

export interface GhostAnnotationPayload {
  id: string;
  title: string;
  content: string;
  target_window_title?: string | null;
  anchor_point: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center' | 'custom';
  offset_x: number;
  offset_y: number;
  screen_x: number;
  screen_y: number;
  opacity: number;
  click_through: boolean;
  created_at: number;
  ttl_seconds?: number | null;
  is_dismissed: boolean;
  style_preset: 'cyber_cyan' | 'neon_amber' | 'matrix_green' | 'crimson_alert';
}

export interface SpatialOverlayStatePayload {
  is_active: boolean;
  click_through: boolean;
  direct_composition_enabled: boolean;
  active_window?: ActiveWindowTargetPayload | null;
  annotations: GhostAnnotationPayload[];
  total_annotations_created: number;
  last_updated: number;
}

export interface SpatialStateMsg extends BaseMessage {
  type: 'spatial_state_update';
  payload: SpatialOverlayStatePayload;
}

export interface SpatialToggleOverlayMsg extends BaseMessage {
  type: 'spatial.toggle_overlay';
  payload: {
    is_active: boolean;
    click_through?: boolean;
  };
}

export interface SpatialDismissAnnotationMsg extends BaseMessage {
  type: 'spatial.dismiss_annotation';
  payload: {
    annotation_id: string;
  };
}

export interface Win32EventPayload {
  event_id: string;
  event_type: 'FOCUS_CHANGE' | 'WINDOW_CRASH' | 'TERMINAL_ERROR_CODE' | 'EXCEPTION_DIALOG' | 'BACKGROUND_MILESTONE' | 'SYSTEM_ALERT';
  process_name: string;
  pid: number;
  window_title: string;
  details: Record<string, any>;
  timestamp: number;
  is_scrubbed: boolean;
  scrubbed_fields: string[];
}

export interface AudioCuePayload {
  cue_id: string;
  cue_type: 'SUBTLE_CHIME' | 'MILESTONE_FANFARE' | 'RISK_GATE_WARNING' | 'GUARDIAN_HALT_BUZZ' | 'DREAM_CYCLE_START' | 'DREAM_CYCLE_COMPLETE';
  frequency_hz: number;
  duration_ms: number;
  volume: number;
  spatial_pan: number;
  timestamp: number;
}

export interface WebRTCMirrorSessionPayload {
  session_id: string;
  device_id: string;
  is_connected: boolean;
  fps_target: number;
  resolution: string;
  local_only: boolean;
  ice_candidates_count: number;
  created_at: number;
}

export interface ProactiveBusEventMsg extends BaseMessage {
  type: 'proactive_bus_event';
  payload: Win32EventPayload;
}

export interface AmbientAudioCueMsg extends BaseMessage {
  type: 'ambient_audio_cue';
  payload: AudioCuePayload;
}

export interface WebRTCMirrorUpdateMsg extends BaseMessage {
  type: 'webrtc_mirror_update';
  payload: WebRTCMirrorSessionPayload;
}

export interface WebRTCMirrorTerminatedMsg extends BaseMessage {
  type: 'webrtc_mirror_terminated';
  payload: {
    session_id: string;
  };
}

export interface ProactiveIngestEventMsg extends BaseMessage {
  type: 'proactive.ingest_event';
  payload: {
    event_type: string;
    process_name?: string;
    pid?: number;
    window_title?: string;
    details?: Record<string, any>;
  };
}

export interface AmbientPlayCueMsg extends BaseMessage {
  type: 'ambient.play_cue';
  payload: {
    cue_type: string;
    spatial_pan?: number;
    volume?: number;
  };
}

export interface WebRTCConnectMsg extends BaseMessage {
  type: 'webrtc.connect';
  payload: {
    device_id: string;
    fps_target?: number;
    resolution?: string;
  };
}

export interface WebRTCDisconnectMsg extends BaseMessage {
  type: 'webrtc.disconnect';
  payload: {
    session_id: string;
  };
}

export interface AdapterMetadataPayload {
  adapter_id: string;
  domain: string;
  base_model: string;
  lora_rank: number;
  lora_alpha: number;
  training_loss: number;
  benchmark_score: number;
  status: 'ACTIVE' | 'STANDBY' | 'TRAINING' | 'EVALUATING' | 'QUARANTINED' | 'ARCHIVED';
  dataset_pairs_count: number;
  created_at: number;
  is_active: boolean;
}

export interface EvaluationBenchmarkReportPayload {
  report_id: string;
  adapter_id: string;
  accuracy_score: number;
  latency_ms: number;
  regression_detected: boolean;
  dataset_size: number;
  passed_threshold: boolean;
  timestamp: number;
}

export interface EvolutionEngineStatusPayload {
  is_running: boolean;
  is_halted: boolean;
  active_adapter?: AdapterMetadataPayload | null;
  registered_adapters: AdapterMetadataPayload[];
  total_instructions_distilled: number;
  last_tuning_timestamp?: number | null;
  last_benchmark_report?: EvaluationBenchmarkReportPayload | null;
}

export interface EvolutionStatusMsg extends BaseMessage {
  type: 'evolution_status_update';
  payload: EvolutionEngineStatusPayload;
}

export interface EvolutionTrainAdapterMsg extends BaseMessage {
  type: 'evolution.train_adapter';
  payload: {
    adapter_id: string;
    domain: string;
    lora_rank?: number;
    lora_alpha?: number;
    epochs?: number;
  };
}

export interface EvolutionActivateAdapterMsg extends BaseMessage {
  type: 'evolution.activate_adapter';
  payload: {
    adapter_id: string;
  };
}

export interface EvolutionRollbackAdapterMsg extends BaseMessage {
  type: 'evolution.rollback_adapter';
  payload: {
    target_adapter_id?: string;
  };
}

// Milestone 13 Phase 2: Volumetric Spatial 3D Canvas & Vision Gestures
export interface Vector3DPayload {
  x: number;
  y: number;
  z: number;
}

export interface VolumetricNodePayload {
  node_id: string;
  label: string;
  position: Vector3DPayload;
  velocity?: Vector3DPayload;
  color_hex: string;
  radius: number;
  is_pinned: boolean;
  depth_layer: number;
  metadata?: Record<string, unknown>;
  created_at: number;
}

export interface VisionGesturePayload {
  gesture_id: string;
  gesture_type: string;
  confidence: number;
  hand_position: Vector3DPayload;
  pinch_distance?: number | null;
  timestamp: number;
}

export interface VolumetricWorkspaceStatePayload {
  is_active: boolean;
  projection_mode: string;
  total_nodes: number;
  nodes: VolumetricNodePayload[];
  active_gesture?: VisionGesturePayload | null;
  multi_monitor_enabled: boolean;
  depth_buffer_enabled: boolean;
  selected_node_id?: string | null;
  last_updated: number;
}

export interface VolumetricStateMsg extends BaseMessage {
  type: 'volumetric_state_update';
  payload: VolumetricWorkspaceStatePayload;
}

export interface VolumetricSetProjectionMsg extends BaseMessage {
  type: 'volumetric.set_projection';
  payload: {
    mode: 'cylindrical' | 'spherical' | 'planar';
  };
}

export interface VolumetricSpawnNodeMsg extends BaseMessage {
  type: 'volumetric.spawn_node';
  payload: {
    label: string;
    x?: number;
    y?: number;
    z?: number;
    color_hex?: string;
    depth_layer?: number;
    is_pinned?: boolean;
  };
}

export interface VolumetricClearCanvasMsg extends BaseMessage {
  type: 'volumetric.clear_canvas';
  payload?: Record<string, unknown>;
}

export interface VolumetricIngestGestureMsg extends BaseMessage {
  type: 'volumetric.ingest_gesture';
  payload: {
    gesture_type: string;
    confidence?: number;
    x?: number;
    y?: number;
    z?: number;
    pinch_distance?: number;
  };
}

// Milestone 13 Phase 3: Distributed Swarm Compute & P2P Mesh Offloading
export interface SwarmNodeTelemetryPayload {
  node_id: string;
  device_name: string;
  node_type: string;
  available_vram_mb: number;
  available_ram_mb: number;
  battery_percent: number;
  is_plugged_in: boolean;
  thermal_throttled: boolean;
  compute_flops_rating: number;
  is_online: boolean;
  last_heartbeat: number;
}

export interface DistributedWorkloadPayload {
  task_id: string;
  workload_type: string;
  payload: Record<string, unknown>;
  assigned_node_id: string;
  status: string;
  assigned_at: number;
  completed_at?: number | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
  failover_count: number;
}

export interface SwarmClusterStatePayload {
  cluster_id: string;
  active_node_count: number;
  total_vram_mb: number;
  total_ram_mb: number;
  nodes: SwarmNodeTelemetryPayload[];
  active_workload_count: number;
  cluster_load_factor: number;
  is_healthy: boolean;
  last_updated: number;
}

export interface SwarmClusterStateMsg extends BaseMessage {
  type: 'swarm_cluster_update';
  payload: SwarmClusterStatePayload;
}

export interface SwarmWorkloadUpdateMsg extends BaseMessage {
  type: 'swarm_workload_update';
  payload: DistributedWorkloadPayload;
}

export interface SwarmRegisterNodeMsg extends BaseMessage {
  type: 'swarm.register_node';
  payload: {
    node_id: string;
    device_name: string;
    node_type?: string;
    available_vram_mb?: number;
    available_ram_mb?: number;
    battery_percent?: number;
    is_plugged_in?: boolean;
    thermal_throttled?: boolean;
    compute_flops_rating?: number;
  };
}

export interface SwarmOffloadWorkloadMsg extends BaseMessage {
  type: 'swarm.offload_workload';
  payload: {
    workload_type: 'SPECULATIVE_DECODING' | 'EMBEDDING_BATCH' | 'DOCUMENT_INDEXING' | 'INFERENCE_PROBE';
    items_count?: number;
    preferred_node_id?: string;
  };
}

export interface SwarmAbortWorkloadMsg extends BaseMessage {
  type: 'swarm.abort_workload';
  payload: {
    task_id: string;
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
  | SpatialStateMsg
  | ProactiveBusEventMsg
  | AmbientAudioCueMsg
  | WebRTCMirrorUpdateMsg
  | WebRTCMirrorTerminatedMsg
  | EvolutionStatusMsg
  | VolumetricStateMsg
  | SwarmClusterStateMsg
  | SwarmWorkloadUpdateMsg
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
  | DreamTriggerCycleMsg
  | SpatialToggleOverlayMsg
  | SpatialDismissAnnotationMsg
  | ProactiveIngestEventMsg
  | AmbientPlayCueMsg
  | WebRTCConnectMsg
  | WebRTCDisconnectMsg
  | EvolutionTrainAdapterMsg
  | EvolutionActivateAdapterMsg
  | EvolutionRollbackAdapterMsg
  | VolumetricSetProjectionMsg
  | VolumetricSpawnNodeMsg
  | VolumetricClearCanvasMsg
  | VolumetricIngestGestureMsg
  | SwarmRegisterNodeMsg
  | SwarmOffloadWorkloadMsg
  | SwarmAbortWorkloadMsg;
