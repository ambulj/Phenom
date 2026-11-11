import React, { useState, useEffect, useRef } from 'react';

import { HeaderBar } from './components/HeaderBar';
import { DeveloperWorkspaceState } from './types/workspace';

import { Orb, OrbQualityLevel } from './components/Orb';

import { ChatBox, sanitizeChatText } from './components/ChatBox';

import { ConfirmationModal } from './components/ConfirmationModal';

import { HistoryPanel } from './components/panels/HistoryPanel';

import { ActionLogPanel } from './components/panels/ActionLogPanel';

import { LearnedRulesPanel } from './components/panels/LearnedRulesPanel';

import { ApprovalsPanel } from './components/panels/ApprovalsPanel';

import { SettingsPanel } from './components/panels/SettingsPanel';

import { LiveViewPanel } from './components/panels/LiveViewPanel';

import { DashboardPanel } from './components/panels/DashboardPanel';

import { MiniOverlay } from './components/MiniOverlay';

import { FirstRunWizard } from './components/FirstRunWizard';

import { ScreenBorderOverlay, ScreenOverlayState, ClickTarget, TickerItem, HudAnnotationItem, AmbientAlertItem } from './components/ScreenBorderOverlay';

import { OrbState, ConfirmRequestPayload, LearnedRuleItem } from './types/protocol';

import { CommandPalette, CommandItem } from './components/CommandPalette';

import { HUDCard, HUDCardProps } from './components/HUDCard';

import { StreamingConsole, ConsoleLine } from './components/StreamingConsole';

import { HumanTakeoverBanner } from './components/CyberHUD/HumanTakeoverBanner';
import { MediaPlayerHUD } from './components/CyberHUD/MediaPlayerHUD';
import { WindowTilerHUD } from './components/CyberHUD/WindowTilerHUD';
import { ActiveModelIndicator } from './components/CyberHUD/ActiveModelIndicator';
import { VoicePersonaHUD } from './components/CyberHUD/VoicePersonaHUD';
import { ContextStreamHUD } from './components/CyberHUD/ContextStreamHUD';
import { TelegramCompanionHUD } from './components/CyberHUD/TelegramCompanionHUD';
import { DocumentSynthesisHUD } from './components/CyberHUD/DocumentSynthesisHUD';
import { BrowserOperatorHUD } from './components/CyberHUD/BrowserOperatorHUD';
import { ParticleOrbHUD } from './components/CyberHUD/ParticleOrbHUD';
import { ScreenVisionHUD } from './components/CyberHUD/ScreenVisionHUD';
import { ProactiveSchedulerHUD } from './components/CyberHUD/ProactiveSchedulerHUD';
import { AssociativeMemoryHUD } from './components/CyberHUD/AssociativeMemoryHUD';
import { WorkspaceCodeHUD } from './components/CyberHUD/WorkspaceCodeHUD';
import { KnowledgeCanvasHUD } from './components/CyberHUD/KnowledgeCanvasHUD';
import { MultimodalFusionHUD } from './components/CyberHUD/MultimodalFusionHUD';
import { MacroWorkflowHUD } from './components/CyberHUD/MacroWorkflowHUD';
import { TelegramMeshHUD } from './components/CyberHUD/TelegramMeshHUD';
import { AdaptiveVoicePersonaHUD } from './components/CyberHUD/AdaptiveVoicePersonaHUD';
import { SwarmOrchestratorHUD } from './components/CyberHUD/SwarmOrchestratorHUD';
import { TemporalReasoningHUD } from './components/CyberHUD/TemporalReasoningHUD';
import { SpatialLayoutHUD } from './components/CyberHUD/SpatialLayoutHUD';
import { AmbientIntelligenceHUD } from './components/CyberHUD/AmbientIntelligenceHUD';
import { MetacognitiveReflectorHUD } from './components/CyberHUD/MetacognitiveReflectorHUD';
import { LoRAAdapterHubHUD } from './components/CyberHUD/LoRAAdapterHubHUD';
import { VoiceCodeSynapseHUD } from './components/CyberHUD/VoiceCodeSynapseHUD';
import { PredictiveTaskHubHUD } from './components/CyberHUD/PredictiveTaskHubHUD';
import { SelfHealingKernelHUD } from './components/CyberHUD/SelfHealingKernelHUD';
import { SandboxExecutionJailHUD } from './components/CyberHUD/SandboxExecutionJailHUD';
import { SpatialVoiceSynapseHUD } from './components/CyberHUD/SpatialVoiceSynapseHUD';
import { ResourceGovernorHUD } from './components/CyberHUD/ResourceGovernorHUD';
import { ScreenGroundingHUD } from './components/CyberHUD/ScreenGroundingHUD';
import { GuiActionPlayerHUD } from './components/CyberHUD/GuiActionPlayerHUD';
import { CrossAppWorkflowHUD } from './components/CyberHUD/CrossAppWorkflowHUD';
import { DesktopWatchdogHUD } from './components/CyberHUD/DesktopWatchdogHUD';
import { MemoryConsolidationHUD } from './components/CyberHUD/MemoryConsolidationHUD';
import { EpistemicBeliefNetworkHUD } from './components/CyberHUD/EpistemicBeliefNetworkHUD';
import { WorldModelSimulatorHUD } from './components/CyberHUD/WorldModelSimulatorHUD';
import { CognitiveLoadBalancerHUD } from './components/CyberHUD/CognitiveLoadBalancerHUD';
import { AgentSwarmMeshHUD } from './components/CyberHUD/AgentSwarmMeshHUD';
import { TaskAuctionProtocolHUD } from './components/CyberHUD/TaskAuctionProtocolHUD';
import { SwarmConsensusCRDTHUD } from './components/CyberHUD/SwarmConsensusCRDTHUD';
import { SwarmWatchdogArbiterHUD } from './components/CyberHUD/SwarmWatchdogArbiterHUD';
import { GoalDecompositionTreeHUD } from './components/CyberHUD/GoalDecompositionTreeHUD';
import { AdaptiveBranchPlannerHUD } from './components/CyberHUD/AdaptiveBranchPlannerHUD';
import { SelfHealingOrchestratorHUD } from './components/CyberHUD/SelfHealingOrchestratorHUD';
import { ExecutionStreamShieldHUD } from './components/CyberHUD/ExecutionStreamShieldHUD';
import { SafetyTierMatrixHUD } from './components/CyberHUD/SafetyTierMatrixHUD';
import { VoiceConfirmationHUD } from './components/CyberHUD/VoiceConfirmationHUD';
import { SilentActivityMonitorHUD } from './components/CyberHUD/SilentActivityMonitorHUD';
import { ScreenIntelligenceHUD } from './components/CyberHUD/ScreenIntelligenceHUD';
import { MultiAgentSwarmHUD } from './components/CyberHUD/MultiAgentSwarmHUD';
import { FullDuplexVoiceHUD } from './components/CyberHUD/FullDuplexVoiceHUD';

import { AutomationTakeoverPromptPayload } from './types/protocol';



export const App: React.FC = () => {

  const [showFirstRun, setShowFirstRun] = useState<boolean>(() => {

    if (typeof window !== 'undefined') {

      if ((window as any).phenom?.isFirstRunDone?.()) return false;

      if (localStorage.getItem('phenom_first_run_done') === 'true') return false;

    }

    return false;

  });

  const [orbState, setOrbState] = useState<OrbState>('idle');

  const [orbQuality, setOrbQuality] = useState<OrbQualityLevel>('high');

  const [isConnected, setIsConnected] = useState<boolean>(false);

  const [activePanel, setActivePanel] = useState<string | null>(null);

  const [streamingText, setStreamingText] = useState<string>('');

  const [isStreaming, setIsStreaming] = useState<boolean>(false);

  const [confirmRequest, setConfirmRequest] = useState<ConfirmRequestPayload | null>(null);

  const [learnedRules, setLearnedRules] = useState<LearnedRuleItem[]>([]);

  const [historyMessages, setHistoryMessages] = useState<Array<{ id: string; role: string; content: string }>>([]);

  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);

  const [isConsoleOpen, setIsConsoleOpen] = useState<boolean>(false);

  const [consoleLines, setConsoleLines] = useState<ConsoleLine[]>([

    { text: 'Phenom Engine v0.1.0 initialized (Windows 11 Mica/Acrylic)', type: 'system', timestamp: new Date().toLocaleTimeString() },

    { text: 'WebSocket link: ws://127.0.0.1:8000/ws', type: 'system', timestamp: new Date().toLocaleTimeString() }

  ]);

  const [activeHudCard, setActiveHudCard] = useState<HUDCardProps | null>(null);
  const [ambientAlerts, setAmbientAlerts] = useState<AmbientAlertItem[]>([]);
  const [workspaceState, setWorkspaceState] = useState<DeveloperWorkspaceState | null>(null);



  // Voice State (Phase 2)

  const [isMuted, setIsMuted] = useState<boolean>(false);

  const [amplitude, setAmplitude] = useState<number>(0);

  const [wakePhrase, setWakePhrase] = useState<string>('hey_jarvis');

  const [hotkeys, setHotkeys] = useState<Record<string, string>>({

    push_to_talk: 'alt+space',

    toggle_phenom: 'ctrl+alt+p',

    kill_switch: 'ctrl+alt+pause'

  });

  const [hotkeyError, setHotkeyError] = useState<string | null>(null);



  // Automation & Screen State (Phase 3)

  const [liveFrame, setLiveFrame] = useState<string | null>(null);

  const [takeoverPrompt, setTakeoverPrompt] = useState<string | null>(null);

  const [takeoverPayload, setTakeoverPayload] = useState<AutomationTakeoverPromptPayload | null>(null);

  const [screenOverlayState, setScreenOverlayState] = useState<ScreenOverlayState>({ state: 'idle' });

  const [clickTarget, setClickTarget] = useState<ClickTarget | null>(null);

  const [tickerItems, setTickerItems] = useState<TickerItem[]>([]);

  const [hudAnnotations, setHudAnnotations] = useState<HudAnnotationItem[]>([]);



  // Modes, Scheduler, & Watchlist State (Phase 5)

  const [currentMode, setCurrentMode] = useState<string>('work');

  const [scheduledJobs, setScheduledJobs] = useState<any[]>([]);

  const [watchlistItems, setWatchlistItems] = useState<any[]>([]);

  const [showMiniOverlay, setShowMiniOverlay] = useState<boolean>(true);
  const [showMediaPlayer, setShowMediaPlayer] = useState<boolean>(false);
  const [mediaExternalEvent, setMediaExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showWindowTiler, setShowWindowTiler] = useState<boolean>(false);
  const [windowTilerExternalEvent, setWindowTilerExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [modelExternalEvent, setModelExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showVoicePersona, setShowVoicePersona] = useState<boolean>(false);
  const [voicePersonaExternalEvent, setVoicePersonaExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showContextStream, setShowContextStream] = useState<boolean>(false);
  const [contextStreamExternalEvent, setContextStreamExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showTelegramCompanion, setShowTelegramCompanion] = useState<boolean>(false);
  const [telegramCompanionExternalEvent, setTelegramCompanionExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showDocumentSynthesis, setShowDocumentSynthesis] = useState<boolean>(false);
  const [documentSynthesisExternalEvent, setDocumentSynthesisExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showBrowserOperator, setShowBrowserOperator] = useState<boolean>(false);
  const [browserOperatorExternalEvent, setBrowserOperatorExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showParticleOrb, setShowParticleOrb] = useState<boolean>(false);
  const [showScreenVision, setShowScreenVision] = useState<boolean>(false);
  const [screenVisionExternalEvent, setScreenVisionExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showProactiveScheduler, setShowProactiveScheduler] = useState<boolean>(false);
  const [proactiveSchedulerExternalEvent, setProactiveSchedulerExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showAssociativeMemory, setShowAssociativeMemory] = useState<boolean>(false);
  const [showWorkspaceCode, setShowWorkspaceCode] = useState<boolean>(false);
  const [workspaceCodeExternalEvent, setWorkspaceCodeExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showKnowledgeCanvas, setShowKnowledgeCanvas] = useState<boolean>(false);
  const [knowledgeCanvasExternalEvent, setKnowledgeCanvasExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showMultimodalFusion, setShowMultimodalFusion] = useState<boolean>(false);
  const [multimodalFusionExternalEvent, setMultimodalFusionExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showMacroWorkflow, setShowMacroWorkflow] = useState<boolean>(false);
  const [macroWorkflowExternalEvent, setMacroWorkflowExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showTelegramMesh, setShowTelegramMesh] = useState<boolean>(false);
  const [telegramMeshExternalEvent, setTelegramMeshExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showAdaptiveVoice, setShowAdaptiveVoice] = useState<boolean>(false);
  const [adaptiveVoiceExternalEvent, setAdaptiveVoiceExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showSwarmOrchestrator, setShowSwarmOrchestrator] = useState<boolean>(false);
  const [swarmOrchestratorExternalEvent, setSwarmOrchestratorExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showTemporalReasoning, setShowTemporalReasoning] = useState<boolean>(false);
  const [temporalReasoningExternalEvent, setTemporalReasoningExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showSpatialLayout, setShowSpatialLayout] = useState<boolean>(false);
  const [spatialLayoutExternalEvent, setSpatialLayoutExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showAmbientIntelligence, setShowAmbientIntelligence] = useState<boolean>(false);
  const [ambientIntelligenceExternalEvent, setAmbientIntelligenceExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showMetacognitiveReflector, setShowMetacognitiveReflector] = useState<boolean>(false);
  const [metacognitiveReflectorExternalEvent, setMetacognitiveReflectorExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showLoRAAdapterHub, setShowLoRAAdapterHub] = useState<boolean>(false);
  const [loraAdapterHubExternalEvent, setLoraAdapterHubExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showVoiceCodeSynapse, setShowVoiceCodeSynapse] = useState<boolean>(false);
  const [voiceCodeSynapseExternalEvent, setVoiceCodeSynapseExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showPredictiveTaskHub, setShowPredictiveTaskHub] = useState<boolean>(false);
  const [predictiveTaskHubExternalEvent, setPredictiveTaskHubExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showSelfHealingKernel, setShowSelfHealingKernel] = useState<boolean>(false);
  const [selfHealingKernelExternalEvent, setSelfHealingKernelExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showSandboxExecutionJail, setShowSandboxExecutionJail] = useState<boolean>(false);
  const [sandboxExecutionJailExternalEvent, setSandboxExecutionJailExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showSpatialVoiceSynapse, setShowSpatialVoiceSynapse] = useState<boolean>(false);
  const [spatialVoiceSynapseExternalEvent, setSpatialVoiceSynapseExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showResourceGovernor, setShowResourceGovernor] = useState<boolean>(false);
  const [resourceGovernorExternalEvent, setResourceGovernorExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showScreenGrounding, setShowScreenGrounding] = useState<boolean>(false);
  const [screenGroundingExternalEvent, setScreenGroundingExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showGuiActionPlayer, setShowGuiActionPlayer] = useState<boolean>(false);
  const [guiActionPlayerExternalEvent, setGuiActionPlayerExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showCrossAppWorkflow, setShowCrossAppWorkflow] = useState<boolean>(false);
  const [crossAppWorkflowExternalEvent, setCrossAppWorkflowExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showDesktopWatchdog, setShowDesktopWatchdog] = useState<boolean>(false);
  const [desktopWatchdogExternalEvent, setDesktopWatchdogExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showMemoryConsolidation, setShowMemoryConsolidation] = useState<boolean>(false);
  const [memoryConsolidationExternalEvent, setMemoryConsolidationExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showEpistemicBeliefNetwork, setShowEpistemicBeliefNetwork] = useState<boolean>(false);
  const [epistemicBeliefNetworkExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showWorldModelSimulator, setShowWorldModelSimulator] = useState<boolean>(false);
  const [worldModelSimulatorExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showCognitiveLoadBalancer, setShowCognitiveLoadBalancer] = useState<boolean>(false);
  const [cognitiveLoadBalancerExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showAgentSwarmMesh, setShowAgentSwarmMesh] = useState<boolean>(false);
  const [agentSwarmMeshExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showTaskAuctionProtocol, setShowTaskAuctionProtocol] = useState<boolean>(false);
  const [taskAuctionProtocolExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showSwarmConsensusCRDT, setShowSwarmConsensusCRDT] = useState<boolean>(false);
  const [swarmConsensusCRDTExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showSwarmWatchdogArbiter, setShowSwarmWatchdogArbiter] = useState<boolean>(false);
  const [swarmWatchdogArbiterExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showGoalDecompositionTree, setShowGoalDecompositionTree] = useState<boolean>(false);
  const [goalDecompositionTreeExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showAdaptiveBranchPlanner, setShowAdaptiveBranchPlanner] = useState<boolean>(false);
  const [adaptiveBranchPlannerExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showSelfHealingOrchestrator, setShowSelfHealingOrchestrator] = useState<boolean>(false);
  const [selfHealingOrchestratorExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showExecutionStreamShield, setShowExecutionStreamShield] = useState<boolean>(false);
  const [executionStreamShieldExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showSafetyTierMatrix, setShowSafetyTierMatrix] = useState<boolean>(false);
  const [safetyTierMatrixExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showVoiceConfirmation, setShowVoiceConfirmation] = useState<boolean>(false);
  const [voiceConfirmationExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showSilentActivityMonitor, setShowSilentActivityMonitor] = useState<boolean>(false);
  const [silentActivityMonitorExternalEvent] = useState<{ type: string; payload?: any } | null>(null);
  const [showScreenIntelligence, setShowScreenIntelligence] = useState<boolean>(false);
  const [showMultiAgentSwarm, setShowMultiAgentSwarm] = useState<boolean>(false);
  const [showFullDuplexVoice, setShowFullDuplexVoice] = useState<boolean>(false);
  const [associativeMemoryExternalEvent, setAssociativeMemoryExternalEvent] = useState<{ type: string; payload?: any } | null>(null);



  const wsRef = useRef<WebSocket | null>(null);



  // Initialize WebSocket connection

  useEffect(() => {

    let reconnectTimeout: any;



    const connect = () => {

      const token = window.phenom?.getSessionToken();

      const protocols = token ? [`phenom.${token}`] : [];

      const ws = new WebSocket('ws://127.0.0.1:8000/ws', protocols);

      wsRef.current = ws;



      ws.onopen = () => {

        setIsConnected(true);

      };



      ws.onmessage = (event) => {

        try {

          const msg = JSON.parse(event.data);

          const mtype = msg.type;

          const payload = msg.payload || {};



          if (mtype === 'state.change') {

            setOrbState(payload.state);

          } else if (mtype === 'orb.quality_level') {

            setOrbQuality(payload.quality || 'high');

          } else if (mtype === 'chat.token') {

            setIsStreaming(true);

            setStreamingText((prev) => prev + payload.token);

          } else if (mtype === 'chat.done') {
            setIsStreaming(false);
            setStreamingText('');
            if (payload.full_text) {
              const cleanFull = sanitizeChatText(payload.full_text);
              if (cleanFull) {
                setHistoryMessages((prev) => [
                  ...prev,
                  { id: `hist-${Date.now()}`, role: 'assistant', content: cleanFull }
                ]);
              }
            }

          } else if (mtype === 'chat.cancelled') {

            setIsStreaming(false);

          } else if (mtype === 'confirm.request') {

            setConfirmRequest(payload);

          } else if (mtype === 'rules.updated') {

            setLearnedRules(payload.rules || []);

          } else if (mtype === 'voice.amplitude') {

            setAmplitude(payload.amplitude ?? 0);

          } else if (mtype === 'voice.status') {

            setIsMuted(payload.muted ?? false);

          } else if (mtype === 'hotkeys.result') {

            if (payload.success) {

              setHotkeys(payload.hotkeys || {});

              setHotkeyError(null);

            } else {

              setHotkeyError(payload.error || 'Failed to update hotkey.');

            }

          } else if (mtype === 'browser.frame') {

            setLiveFrame(payload.image_data);

          } else if (mtype === 'screen.overlay_state') {

            setScreenOverlayState(payload);

            if (payload.state === 'success' || payload.state === 'error') {

              setTimeout(() => {

                setScreenOverlayState({ state: 'idle' });

                setTickerItems([]);

              }, 2500);

            }

          } else if (mtype === 'screen.click_highlight') {

            setClickTarget({ x: payload.x, y: payload.y, durationMs: payload.duration_ms || 300 });

            setTimeout(() => setClickTarget(null), payload.duration_ms || 300);

          } else if (mtype === 'vision.annotations') {

            const annos = payload.annotations || [];

            setHudAnnotations(annos);

            const duration = payload.duration_ms || 3000;

            setTimeout(() => {

              setHudAnnotations([]);

            }, duration);

          } else if (mtype === 'vision.clear_annotations') {

            setHudAnnotations([]);

          } else if (mtype === 'screen.action_ticker') {

            setTickerItems((prev) => [...prev.slice(-5), payload]);

          } else if (mtype === 'automation.takeover_prompt') {

            setTakeoverPayload(payload as AutomationTakeoverPromptPayload);

            setTakeoverPrompt(payload.reason || 'User interaction detected during automation.');

            setActivePanel('live_view'); // Automatically surface the Live View with prompt

          } else if (mtype === 'ambient.alert') {
            const alertItem = payload as AmbientAlertItem;
            setAmbientAlerts((prev) => [...prev.slice(-3), alertItem]);
            const autoDismiss = (alertItem.auto_dismiss_seconds || 6) * 1000;
            setTimeout(() => {
              setAmbientAlerts((prev) => prev.filter((a) => a.id !== alertItem.id));
            }, autoDismiss);
          } else if (mtype.startsWith('media.') || mtype.startsWith('MEDIA_')) {
            setMediaExternalEvent({ type: mtype, payload });
            setShowMediaPlayer(true);
          } else if (mtype.startsWith('WINDOW_') || mtype.startsWith('MACRO_')) {
            setWindowTilerExternalEvent({ type: mtype, payload });
            setShowWindowTiler(true);
          } else if (mtype === 'MODEL_ROUTED' || mtype === 'MODEL_ROUTING_OVERRIDE_CHANGED') {
            setModelExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('VOICE_PERSONA_')) {
            setVoicePersonaExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('CONTEXT_')) {
            setContextStreamExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('TELEGRAM_')) {
            setTelegramCompanionExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('DOCUMENT_') || mtype === 'document_generated' || mtype === 'documents_list_update') {
            setDocumentSynthesisExternalEvent({ type: mtype, payload });
            setShowDocumentSynthesis(true);
          } else if (mtype.startsWith('browser.') || mtype.startsWith('BROWSER_')) {
            setBrowserOperatorExternalEvent({ type: mtype, payload });
            setShowBrowserOperator(true);
          } else if (mtype.startsWith('memory.')) {
            setAssociativeMemoryExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('code.')) {
            setWorkspaceCodeExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('obsidian.')) {
            setKnowledgeCanvasExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('fusion.')) {
            setMultimodalFusionExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('workflow.') || mtype.startsWith('macro.')) {
            setMacroWorkflowExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('telegram.mesh') || mtype.startsWith('mesh.')) {
            setTelegramMeshExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('voice.adaptive') || mtype.startsWith('persona.')) {
            setAdaptiveVoiceExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('swarm.dag') || mtype.startsWith('dag.')) {
            setSwarmOrchestratorExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('reasoning.') || mtype.startsWith('temporal.')) {
            setTemporalReasoningExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('spatial.layout') || mtype.startsWith('layout.')) {
            setSpatialLayoutExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('ambient.feed') || mtype.startsWith('ambient.intel')) {
            setAmbientIntelligenceExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('metacognition.') || mtype.startsWith('reflection.')) {
            setMetacognitiveReflectorExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('evolution.') || mtype.startsWith('adapter.')) {
            setLoraAdapterHubExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('synapse.') || mtype.startsWith('code.voice')) {
            setVoiceCodeSynapseExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('predictive.') || mtype.startsWith('anticipation.') || mtype.startsWith('pipelining.')) {
            setPredictiveTaskHubExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('healing.') || mtype.startsWith('diagnostic.') || mtype.startsWith('patch.')) {
            setSelfHealingKernelExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('sandbox.') || mtype.startsWith('jail.') || mtype.startsWith('security.')) {
            setSandboxExecutionJailExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('spatial.voice') || mtype.startsWith('deictic.') || mtype.startsWith('cursor.')) {
            setSpatialVoiceSynapseExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('governor.') || mtype.startsWith('resource.')) {
            setResourceGovernorExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('grounding.') || mtype.startsWith('visual.')) {
            setScreenGroundingExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('actor.') || mtype.startsWith('gui.action')) {
            setGuiActionPlayerExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('workflow.') || mtype.startsWith('crossapp.') || mtype.startsWith('window.')) {
            setCrossAppWorkflowExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('watchdog.') || mtype.startsWith('incident.') || mtype.startsWith('alert.')) {
            setDesktopWatchdogExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('consolidation.') || mtype.startsWith('memory.graph')) {
            setMemoryConsolidationExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('scheduler.') || mtype.startsWith('proactive.')) {
            setProactiveSchedulerExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('screen.') || mtype.startsWith('gui.') || mtype.startsWith('SCREEN_VISION_')) {
            setScreenVisionExternalEvent({ type: mtype, payload });
          } else if (mtype.startsWith('orb.') || mtype.startsWith('wake.') || mtype.startsWith('whisper.')) {
            setShowParticleOrb(true);
          } else if (mtype === 'mode.changed') {

            setCurrentMode(payload.mode || 'work');

          } else if (mtype === 'scheduler.list_result') {

            setScheduledJobs(payload.jobs || []);

          } else if (mtype === 'scheduler.reminder') {

            setHistoryMessages((prev) => [

              ...prev,

              { id: `rem-${Date.now()}`, role: 'assistant', content: `⏰ **Scheduled Reminder:** ${payload.title}` }

            ]);

          } else if (mtype === 'watchlist.list_result') {

            setWatchlistItems(payload.items || []);

          } else if (mtype === 'PROACTIVE_CARD' || mtype === 'proactive.card') {
            const card = payload.card || msg.card || payload;
            setActiveHudCard({
              title: card.title || 'Proactive Recommendation',
              message: card.description || '',
              badge: "PROACTIVE: " + (card.event_type || "INTEL"),
              type: card.priority >= 3 ? 'approval' : 'info',
              actions: card.action_chip ? [
                {
                  label: card.action_chip,
                  onClick: () => {
                    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                      wsRef.current.send(JSON.stringify({
                        type: 'proactive.action',
                        payload: { card_id: card.id, action_payload: card.action_payload }
                      }));
                    }
                    setActiveHudCard(null);
                  },
                  variant: card.priority >= 3 ? 'danger' : 'primary'
                },
                {
                  label: 'Dismiss',
                  onClick: () => {
                    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                      wsRef.current.send(JSON.stringify({
                        type: 'proactive.dismiss',
                        payload: { card_id: card.id }
                      }));
                    }
                    setActiveHudCard(null);
                  },
                  variant: 'secondary'
                }
              ] : [
                {
                  label: 'Dismiss',
                  onClick: () => setActiveHudCard(null),
                  variant: 'secondary'
                }
              ]
            });
          } else if (mtype === 'DEV_WORKSPACE_UPDATE' || mtype === 'dev.workspace_update') {
            const wsState = payload as DeveloperWorkspaceState;
            setWorkspaceState(wsState);
          } else if (mtype === 'PROACTIVE_ORB_PULSE' || mtype === 'proactive.orb_pulse') {
            setOrbState((prev) => (prev === 'idle' ? 'listening' : prev));
            setTimeout(() => {
              setOrbState((prev) => (prev === 'listening' ? 'idle' : prev));
            }, 3000);

          }

        } catch (e) {

          console.error('Error handling WebSocket message:', e);

        }

      };



      ws.onclose = () => {

        setIsConnected(false);

        reconnectTimeout = setTimeout(connect, 2000);

      };



      ws.onerror = () => {

        ws.close();

      };

    };



    connect();



    return () => {

      clearTimeout(reconnectTimeout);

      wsRef.current?.close();

    };

  }, []);



  const handleSendMessage = (text: string) => {

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    setStreamingText('');

    setIsStreaming(true);

    setHistoryMessages((prev) => [

      ...prev,

      { id: `hist-${Date.now()}`, role: 'user', content: text }

    ]);

    wsRef.current.send(

      JSON.stringify({

        id: `send-${Date.now()}`,

        type: 'chat.send',

        ts: new Date().toISOString(),

        payload: { prompt: text }

      })

    );

  };



  const handleCancelMessage = () => {

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(

      JSON.stringify({

        id: `cancel-${Date.now()}`,

        type: 'chat.cancel',

        ts: new Date().toISOString(),

        payload: {}

      })

    );

  };



  const handleConfirmResponse = (decision: 'approved' | 'denied', rememberChoice: boolean) => {

    if (!wsRef.current || !confirmRequest) return;

    wsRef.current.send(

      JSON.stringify({

        id: `conf-reply-${Date.now()}`,

        type: 'confirm.reply',

        ts: new Date().toISOString(),

        payload: {

          request_id: confirmRequest.request_id,

          decision,

          remember_choice: rememberChoice,

          folder_path: confirmRequest.folder_path

        }

      })

    );

    setConfirmRequest(null);

  };



  const handleTriggerKillswitch = () => {

    if (!wsRef.current) return;

    wsRef.current.send(

      JSON.stringify({

        id: `ks-${Date.now()}`,

        type: 'killswitch.trigger',

        ts: new Date().toISOString(),

        payload: {}

      })

    );

  };



  const handleResume = () => {

    if (!wsRef.current) return;

    wsRef.current.send(

      JSON.stringify({

        id: `resume-${Date.now()}`,

        type: 'killswitch.resume',

        ts: new Date().toISOString(),

        payload: {}

      })

    );

  };



  const handleDeleteRule = (id: string) => {

    if (!wsRef.current) return;

    wsRef.current.send(

      JSON.stringify({

        id: `rule-del-${Date.now()}`,

        type: 'rules.delete',

        ts: new Date().toISOString(),

        payload: { rule_id: id }

      })

    );

  };



  const handleEditRule = (id: string, text: string) => {

    if (!wsRef.current) return;

    wsRef.current.send(

      JSON.stringify({

        id: `rule-edit-${Date.now()}`,

        type: 'rules.edit',

        ts: new Date().toISOString(),

        payload: { rule_id: id, rule_text: text }

      })

    );

  };



  // Voice Handlers

  const handleToggleMute = () => {

    if (!wsRef.current) return;

    const newMute = !isMuted;

    setIsMuted(newMute);

    wsRef.current.send(

      JSON.stringify({

        id: `mute-${Date.now()}`,

        type: 'voice.mute',

        ts: new Date().toISOString(),

        payload: { muted: newMute }

      })

    );

  };



  const handleTriggerVoice = () => {

    if (!wsRef.current) return;

    wsRef.current.send(

      JSON.stringify({

        id: `voice-trig-${Date.now()}`,

        type: 'voice.trigger',

        ts: new Date().toISOString(),

        payload: {}

      })

    );

  };



  const handleUpdateHotkey = (action: string, keyCombo: string) => {

    if (!wsRef.current) return;

    setHotkeyError(null);

    wsRef.current.send(

      JSON.stringify({

        id: `hotkey-${Date.now()}`,

        type: 'hotkeys.update',

        ts: new Date().toISOString(),

        payload: { action, key_combo: keyCombo }

      })

    );

  };



  const handleSetWakePhrase = (phrase: string) => {

    setWakePhrase(phrase);

    if (!wsRef.current) return;

    wsRef.current.send(

      JSON.stringify({

        id: `wake-${Date.now()}`,

        type: 'settings.update',

        ts: new Date().toISOString(),

        payload: { settings: { wake_phrase: phrase } }

      })

    );

  };



  // Automation Handlers (Phase 3)

  const handleTakeoverDecision = (decision: 'continue' | 'stop', sessionId?: string | null) => {

    if (!wsRef.current) return;

    setTakeoverPrompt(null);
    setTakeoverPayload(null);

    wsRef.current.send(

      JSON.stringify({

        id: `takeover-reply-${Date.now()}`,

        type: 'automation.takeover_reply',

        ts: new Date().toISOString(),

        payload: { decision, session_id: sessionId }

      })

    );

  };



  // Modes & Scheduler Handlers (Phase 5)

  const handleCycleMode = () => {

    if (!wsRef.current) return;

    wsRef.current.send(

      JSON.stringify({

        id: `mode-cycle-${Date.now()}`,

        type: 'mode.cycle',

        ts: new Date().toISOString(),

        payload: {}

      })

    );

  };



  const handleSendWs = (msg: any) => {

    if (!wsRef.current) return;

    wsRef.current.send(

      JSON.stringify({

        id: `ws-${Date.now()}`,

        ts: new Date().toISOString(),

        ...msg

      })

    );

  };



  useEffect(() => {

    const handleGlobalKeyDown = (e: KeyboardEvent) => {

      // Alt+Space or Ctrl+K opens Command Palette

      if ((e.altKey && (e.code === 'Space' || e.key === ' ')) || (e.ctrlKey && e.key.toLowerCase() === 'k')) {

        e.preventDefault();

        setIsCommandPaletteOpen((prev) => !prev);

      }

      // Ctrl+` toggles terminal streaming console

      if (e.ctrlKey && (e.key === '`' || e.key === '~')) {

        e.preventDefault();

        setIsConsoleOpen((prev) => !prev);

      }

    };

    window.addEventListener('keydown', handleGlobalKeyDown);

    return () => window.removeEventListener('keydown', handleGlobalKeyDown);

  }, []);



  const paletteCommands: CommandItem[] = [

    {

      id: 'cmd-doctor',

      title: 'Run Phenom Doctor',

      subtitle: 'Inspect CUDA, GPU VRAM, Python, Node, Git, and Ollama toolchains',

      category: 'Dev',

      shortcut: 'Alt+D',

      onExecute: () => handleSendMessage('/doctor')

    },

    {

      id: 'cmd-pre-push',

      title: 'Execute Git Pre-Push Gate',

      subtitle: 'Audit secret leakage, verify tests, and draft PR release notes',

      category: 'Git',

      shortcut: 'Alt+G',

      onExecute: () => handleSendMessage('/git-gate')

    },

    {

      id: 'cmd-console',

      title: 'Toggle Streaming Terminal Console',

      subtitle: 'View live execution stdout/stderr and system logs',

      category: 'Dev',

      shortcut: 'Ctrl+`',

      onExecute: () => setIsConsoleOpen((prev) => !prev)

    },

    {

      id: 'cmd-mode-work',

      title: 'Cycle Operating Mode',

      subtitle: `Current mode: ${currentMode.toUpperCase()}`,

      category: 'System',

      onExecute: () => handleCycleMode()

    },

    {

      id: 'cmd-killswitch',

      title: 'Emergency Halt (Kill Switch)',

      subtitle: 'Immediately abort all processes and speech',

      category: 'System',

      shortcut: 'Esc Esc Esc',

      onExecute: handleTriggerKillswitch

    },

    {

      id: 'cmd-persona-stark',

      title: 'Switch Persona: Tony Stark',

      subtitle: 'Default witty, high-banter lab partner tone',

      category: 'Assistant',

      onExecute: () => handleSendMessage('Switch to Tony Stark persona')

    },

    {

      id: 'cmd-persona-prof',

      title: 'Switch Persona: Professor Mode',

      subtitle: 'Deep technical rigor, formal mechanics, zero slang',

      category: 'Assistant',

      onExecute: () => handleSendMessage('Switch to Professor persona')

    },

    {

      id: 'cmd-persona-silent',

      title: 'Toggle Cyber HUD Media Player',
      subtitle: 'Open or dock YouTube and Spotify embedded player',
      category: 'Assistant',
      onExecute: () => setShowMediaPlayer((prev) => !prev)
    },
    {
      id: 'cmd-toggle-window-tiler',
      title: 'Toggle Window Tiler & Macro Dashboard',
      subtitle: 'Open native Win32 window layout manager and macro recorder HUD',
      category: 'Assistant',
      onExecute: () => setShowWindowTiler((prev) => !prev)
    },
    {
      id: 'cmd-toggle-voice-persona',
      title: 'Toggle Voice Persona & Prosody HUD',
      subtitle: 'View emotion telemetry, cadence rate, and lock persona voice styles',
      category: 'Assistant',
      onExecute: () => setShowVoicePersona((prev) => !prev)
    },
    {
      id: 'cmd-toggle-context-stream',
      title: 'Toggle Context Fusion HUD',
      subtitle: 'Inspect active workspace foreground/background multi-app stream',
      category: 'Assistant',
      onExecute: () => setShowContextStream((prev) => !prev)
    },
    {
      id: 'cmd-toggle-telegram-companion',
      title: 'Toggle Telegram Companion HUD',
      subtitle: 'Manage remote mobile controls, quick action buttons, and snapshot previews',
      category: 'Assistant',
      onExecute: () => setShowTelegramCompanion((prev) => !prev)
    },
    {
      id: 'cmd-toggle-document-synthesis',
      title: 'Toggle Document Synthesis HUD',
      subtitle: 'Autonomous Word, Excel, PowerPoint & PDF generation, charts, and Obsidian hub',
      category: 'Assistant',
      onExecute: () => setShowDocumentSynthesis((prev) => !prev)
    },
    {
      id: 'cmd-toggle-browser-operator',
      title: 'Toggle Browser Operator HUD',
      subtitle: 'Persistent Playwright sovereign web agent & live viewport stream',
      category: 'Assistant',
      onExecute: () => setShowBrowserOperator((prev) => !prev)
    },
    {
      id: 'cmd-associative-memory',
      title: 'Toggle Associative Memory HUD',
      subtitle: 'Search 384-d dense vector knowledge graph, view similarity scores, and manage memories',
      category: 'Assistant',
      onExecute: () => setShowAssociativeMemory((prev) => !prev)
    },
    {
      id: 'cmd-workspace-code-hud',
      title: 'Toggle Workspace Code & Symbol HUD',
      subtitle: 'Explore AST symbols, find callers & preview multi-file atomic refactor diffs',
      category: 'Assistant',
      onExecute: () => setShowWorkspaceCode((prev) => !prev)
    },
    {
      id: 'cmd-knowledge-canvas-hud',
      title: 'Toggle Knowledge Canvas & Cross-Vault HUD',
      subtitle: 'Interactive Obsidian graph, cross-vault wikilinks, hybrid RAG inspector & worktree monitor',
      category: 'Assistant',
      onExecute: () => setShowKnowledgeCanvas((prev) => !prev)
    },
    {
      id: 'cmd-multimodal-fusion-hud',
      title: 'Toggle Multimodal Context Fusion HUD',
      subtitle: 'Live 4-channel matrix (Voice, Window, OCR, AST) & deictic reference resolution',
      category: 'Assistant',
      onExecute: () => setShowMultimodalFusion((prev) => !prev)
    },
    {
      id: 'cmd-macro-workflow-hud',
      title: 'Toggle Desktop Macro Synthesis & Workflow HUD',
      subtitle: 'Synthesize parameterized YAML workflows, test step execution & self-healing element retargeting',
      category: 'Assistant',
      onExecute: () => setShowMacroWorkflow((prev) => !prev)
    },
    {
      id: 'cmd-telegram-mesh-hud',
      title: 'Toggle Telegram Mobile Mesh HUD',
      subtitle: 'Live interactive approval queue, remote voice RAG feed & emergency /halt control',
      category: 'Assistant',
      onExecute: () => setShowTelegramMesh((prev) => !prev)
    },
    {
      id: 'cmd-adaptive-voice-hud',
      title: 'Toggle Adaptive Neural Voice & Persona HUD',
      subtitle: 'Dynamic prosody presets, live waveform monitor & automatic audio ducking',
      category: 'Assistant',
      onExecute: () => setShowAdaptiveVoice((prev) => !prev)
    },
    {
      id: 'cmd-swarm-orchestrator-hud',
      title: 'Toggle Dynamic Swarm Task Graph (DAG) HUD',
      subtitle: 'Inspect topological wave partitioning, dynamic subagent delegation & live node states',
      category: 'Assistant',
      onExecute: () => setShowSwarmOrchestrator((prev) => !prev)
    },
    {
      id: 'cmd-temporal-reasoning-hud',
      title: 'Toggle Temporal Intent Memory & Reasoning HUD',
      subtitle: 'Inspect preference lineage, counterfactual decision rationale & alternative evaluations',
      category: 'Assistant',
      onExecute: () => setShowTemporalReasoning((prev) => !prev)
    },
    {
      id: 'cmd-spatial-layout-hud',
      title: 'Toggle Multi-Display Spatial Layout HUD',
      subtitle: 'Choreograph desktop windows across monitors with task presets & reversible rollback',
      category: 'Assistant',
      onExecute: () => setShowSpatialLayout((prev) => !prev)
    },
    {
      id: 'cmd-ambient-intelligence-hud',
      title: 'Toggle Ambient Intelligence & Priority Hub HUD',
      subtitle: 'Inspect proactive alerts, system health, and regulate focus filtering thresholds',
      category: 'Assistant',
      onExecute: () => setShowAmbientIntelligence((prev) => !prev)
    },
    {
      id: 'cmd-metacognitive-reflector-hud',
      title: 'Toggle Metacognitive Reflector & Calibration HUD',
      subtitle: 'Inspect execution trajectory post-mortems, epistemic confidence & calibration stats',
      category: 'Assistant',
      onExecute: () => setShowMetacognitiveReflector((prev) => !prev)
    },
    {
      id: 'cmd-lora-adapter-hub-hud',
      title: 'Toggle LoRA Adapter Hub & Evolution HUD',
      subtitle: 'Monitor task-specific PEFT adapters, local GPU VRAM allocations & dataset volumes',
      category: 'Assistant',
      onExecute: () => setShowLoRAAdapterHub((prev) => !prev)
    },
    {
      id: 'cmd-voice-code-synapse-hud',
      title: 'Toggle Voice-Code Synapse & AST Co-Editor HUD',
      subtitle: 'Real-time conversational AST code mutations, dry-run diffs & acoustic earcons',
      category: 'Assistant',
      onExecute: () => setShowVoiceCodeSynapse((prev) => !prev)
    },
    {
      id: 'cmd-predictive-task-hub-hud',
      title: 'Toggle Predictive Task Anticipation & Ambient Pipelining HUD',
      subtitle: 'Markov workflow state transitions, proactive action cards & cache pre-warming',
      category: 'Assistant',
      onExecute: () => setShowPredictiveTaskHub((prev) => !prev)
    },
    {
      id: 'cmd-self-healing-kernel-hud',
      title: 'Toggle Self-Healing Kernel HUD',
      subtitle: 'Automated traceback diagnosis, AST fault localization, and reversible patch synthesis',
      category: 'Assistant',
      onExecute: () => setShowSelfHealingKernel((prev) => !prev)
    },
    {
      id: 'cmd-sandbox-execution-jail-hud',
      title: 'Toggle Sandbox Execution Jail HUD',
      subtitle: 'Static AST security auditing, capability-gated ephemeral execution, and timeout enforcement',
      category: 'Assistant',
      onExecute: () => setShowSandboxExecutionJail((prev) => !prev)
    },
    {
      id: 'cmd-spatial-voice-synapse-hud',
      title: 'Toggle Spatial Cursor-Voice Intent Synapse HUD',
      subtitle: 'Cross-modal deictic speech and screen coordinate intent resolver (< 35ms SLA)',
      category: 'Assistant',
      onExecute: () => setShowSpatialVoiceSynapse((prev) => !prev)
    },
    {
      id: 'cmd-resource-governor-hud',
      title: 'Toggle Predictive Resource Governor HUD',
      subtitle: 'Dynamic heterogeneous CUDA/RAM balancing, telemetry monitoring, and emergency throttling',
      category: 'Assistant',
      onExecute: () => setShowResourceGovernor((prev) => !prev)
    },
    {
      id: 'cmd-screen-grounding-hud',
      title: 'Toggle GUI Semantic Grounding HUD',
      subtitle: 'Real-time multi-modal screen element segmentation and natural language coordinate grounding',
      category: 'Assistant',
      onExecute: () => setShowScreenGrounding((prev) => !prev)
    },
    {
      id: 'cmd-gui-action-player-hud',
      title: 'Toggle Declarative GUI Action Player HUD',
      subtitle: 'Safe multi-step GUI interaction plan executor with human takeover protection',
      category: 'Assistant',
      onExecute: () => setShowGuiActionPlayer((prev) => !prev)
    },
    {
      id: 'cmd-cross-app-workflow-hud',
      title: 'Toggle Cross-App Workflow Orchestrator HUD',
      subtitle: 'Ambient multi-application data pipelining, state machines, and window focus synchronization',
      category: 'Assistant',
      onExecute: () => setShowCrossAppWorkflow((prev) => !prev)
    },
    {
      id: 'cmd-desktop-watchdog-hud',
      title: 'Toggle Desktop Watchdog & Interceptor HUD',
      subtitle: 'Proactive context-aware desktop incident monitoring, stability gauge, and 1-click remediation',
      category: 'Assistant',
      onExecute: () => setShowDesktopWatchdog((prev) => !prev)
    },
    {
      id: 'cmd-memory-consolidation-hud',
      title: 'Toggle Memory Consolidation HUD',
      subtitle: 'Episodic session trace consolidation, hierarchical abstraction levels, and decay soft-pruning',
      category: 'Assistant',
      onExecute: () => setShowMemoryConsolidation((prev) => !prev)
    },
    {
      id: 'cmd-epistemic-belief-hud',
      title: 'Toggle Epistemic Belief Network HUD',
      subtitle: 'Bayesian proposition weights, contradiction detection, and revision audit history',
      category: 'Assistant',
      onExecute: () => setShowEpistemicBeliefNetwork((prev) => !prev)
    },
    {
      id: 'cmd-world-model-simulator-hud',
      title: 'Toggle World-Model Simulator HUD',
      subtitle: 'Counterfactual plan projection, feasibility scoring, and collateral side-effect forecasting',
      category: 'Assistant',
      onExecute: () => setShowWorldModelSimulator((prev) => !prev)
    },
    {
      id: 'cmd-cognitive-load-balancer-hud',
      title: 'Toggle Cognitive Load Balancer HUD',
      subtitle: 'Attentional focus pacing, interaction velocity meters, and deferred notification queue',
      category: 'Assistant',
      onExecute: () => setShowCognitiveLoadBalancer((prev) => !prev)
    },
    {
      id: 'cmd-agent-swarm-mesh-hud',
      title: 'Toggle Agent Swarm Mesh HUD',
      subtitle: 'Specialist worker node topology, P2P asynchronous mailboxes, and swarm metrics',
      category: 'Assistant',
      onExecute: () => setShowAgentSwarmMesh((prev) => !prev)
    },
    {
      id: 'cmd-task-auction-protocol-hud',
      title: 'Toggle Task Auction Protocol HUD',
      subtitle: 'DAG dependency contracts, specialist worker bidding matrix, and contract awards',
      category: 'Assistant',
      onExecute: () => setShowTaskAuctionProtocol((prev) => !prev)
    },
    {
      id: 'cmd-swarm-consensus-crdt-hud',
      title: 'Toggle Swarm Consensus CRDT HUD',
      subtitle: 'Lamport vector clocks, distributed state convergence, and LWW delta resolution',
      category: 'Assistant',
      onExecute: () => setShowSwarmConsensusCRDT((prev) => !prev)
    },
    {
      id: 'cmd-swarm-watchdog-arbiter-hud',
      title: 'Toggle Swarm Watchdog & Arbiter HUD',
      subtitle: 'Byzantine worker anomaly radar, node quarantine, and task failover rescue',
      category: 'Assistant',
      onExecute: () => setShowSwarmWatchdogArbiter((prev) => !prev)
    },
    {
      id: 'cmd-goal-decomposition-tree-hud',
      title: 'Toggle Goal Decomposition Tree HUD',
      subtitle: 'Recursive multi-tier plan tree, DAG subtasks, and progress tracking',
      category: 'Assistant',
      onExecute: () => setShowGoalDecompositionTree((prev) => !prev)
    },
    {
      id: 'cmd-adaptive-branch-planner-hud',
      title: 'Toggle Adaptive Branch Planner HUD',
      subtitle: 'Speculative multi-path candidate branches, Monte Carlo feasibility, and branch pruning',
      category: 'Assistant',
      onExecute: () => setShowAdaptiveBranchPlanner((prev) => !prev)
    },
    {
      id: 'cmd-self-healing-orchestrator-hud',
      title: 'Toggle Self-Healing Orchestrator HUD',
      subtitle: 'Dynamic failure interception, error taxonomy classification, and compensatory plan grafting',
      category: 'Assistant',
      onExecute: () => setShowSelfHealingOrchestrator((prev) => !prev)
    },
    {
      id: 'cmd-execution-stream-shield-hud',
      title: 'Toggle Execution Stream Shield HUD',
      subtitle: 'Zero-noise chat stream filter, leak purger, and adaptive persona tuner',
      category: 'Assistant',
      onExecute: () => setShowExecutionStreamShield((prev) => !prev)
    },
    {
      id: 'cmd-safety-tier-matrix-hud',
      title: 'Toggle Safety Tier Matrix HUD',
      subtitle: 'Zero-prompt auto-execution matrix, risk tiers, and high-risk boundary gating',
      category: 'Assistant',
      onExecute: () => setShowSafetyTierMatrix((prev) => !prev)
    },
    {
      id: 'cmd-voice-confirmation-hud',
      title: 'Toggle Voice Confirmation HUD',
      subtitle: 'Natural spoken confirmation prompts, audio wave visualizer, and 1-click approvals',
      category: 'Assistant',
      onExecute: () => setShowVoiceConfirmation((prev) => !prev)
    },
    {
      id: 'cmd-silent-activity-monitor-hud',
      title: 'Toggle Silent Activity Monitor HUD',
      subtitle: 'Real-time background tool execution waterfall, latencies, and parameter inspector',
      category: 'Assistant',
      onExecute: () => setShowSilentActivityMonitor((prev) => !prev)
    },
    {
      id: 'cmd-screen-intelligence-hud',
      title: 'Toggle Screen Intelligence HUD',
      subtitle: 'Real-time offline VLM task tracker, visual UI bounding boxes, and screen-region OCR',
      category: 'Assistant',
      onExecute: () => setShowScreenIntelligence((prev) => !prev)
    },
    {
      id: 'cmd-multi-agent-swarm-hud',
      title: 'Toggle Local Multi-Agent Swarm HUD',
      subtitle: 'Actor-based subagent fleet (Coder, Research, Executive) with live task queue and emergency halt',
      category: 'Assistant',
      onExecute: () => setShowMultiAgentSwarm((prev) => !prev)
    },
    {
      id: 'cmd-full-duplex-voice-hud',
      title: 'Toggle Full-Duplex Voice & Barge-In HUD',
      subtitle: 'Sub-15ms speech interruption with Silero VAD ONNX and natural turn-taking state machine',
      category: 'Assistant',
      onExecute: () => setShowFullDuplexVoice((prev) => !prev)
    },
    {
      id: 'cmd-proactive-scheduler',
      title: 'Toggle Proactive Scheduler HUD',
      subtitle: 'Manage autonomous background daemon, 08:30 AM morning briefing, and file watcher',
      category: 'Assistant',
      onExecute: () => setShowProactiveScheduler((prev) => !prev)
    },
    {
      id: 'cmd-screen-vision',
      title: 'Toggle Screen Vision Viewport HUD',
      subtitle: 'Inspect Smart Context active window capture, UIA target bounding boxes, and Rule 8 shield',
      category: 'Assistant',
      onExecute: () => setShowScreenVision((prev) => !prev)
    },
    {
      id: 'cmd-particle-orb',
      title: 'Toggle Reactive 3D Particle Orb HUD',
      subtitle: 'Sound-reactive Three.js WebGL particle orb & wake-word controls',
      category: 'Assistant',
      onExecute: () => setShowParticleOrb((prev) => !prev)
    },
    {
      id: 'cmd-persona-silent',
      title: 'Switch Persona: Silent Co-Pilot',

      subtitle: 'Visual HUD diffs and code summaries only',

      category: 'Assistant',

      onExecute: () => handleSendMessage('Switch to Silent Co-Pilot persona')

    }

  ];



  const isPanelOpen = activePanel !== null;



  return (

    <div style={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden', background: '#0b0f19' }}>

      <HeaderBar

        orbState={orbState}

        activePanel={activePanel}

        onSelectPanel={setActivePanel}

        onTriggerKillswitch={handleTriggerKillswitch}

        onResume={handleResume}

        isConnected={isConnected}

        isMuted={isMuted}

        onToggleMute={handleToggleMute}

        currentMode={currentMode}

        onCycleMode={handleCycleMode}

        showMiniOverlay={showMiniOverlay}

        onToggleMiniOverlay={() => setShowMiniOverlay((prev) => !prev)}

        onOpenPalette={() => setIsCommandPaletteOpen(true)}

        onToggleConsole={() => setIsConsoleOpen((prev) => !prev)}
        workspaceState={workspaceState}

      />

      {/* Task-Aware Dynamic Model Indicator (MOD-01) */}
      <div style={{ position: 'absolute', top: 12, right: 300, zIndex: 110 }}>
        <ActiveModelIndicator
          externalEvent={modelExternalEvent}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      </div>



      {/* 3D Three.js Orb with Adaptive LOD */}

      <Orb state={orbState} isShrunk={isPanelOpen} amplitude={amplitude} qualityLevel={orbQuality} />



      {/* Main Chat Interface */}

      <ChatBox

        orbState={orbState}

        onSendMessage={handleSendMessage}

        onCancelMessage={handleCancelMessage}

        onClearHistory={() => setHistoryMessages([])}

        onTriggerVoice={handleTriggerVoice}

        streamingText={streamingText}

        isStreaming={isStreaming}

        isShrunk={isPanelOpen}

        messages={historyMessages}

      />



      {/* First Run Setup Wizard (Phase 7) */}

      {showFirstRun && (

        <FirstRunWizard onComplete={() => setShowFirstRun(false)} />

      )}



      {/* Confirmation Modal */}

      <ConfirmationModal

        request={confirmRequest}

        onRespond={handleConfirmResponse}

      />



      {/* Embedded Cyber HUD Media Player (MED-01) */}
      {showMediaPlayer && (
        <div style={{ position: 'absolute', bottom: 90, right: 24, zIndex: 120 }}>
          <MediaPlayerHUD
            externalEvent={mediaExternalEvent}
            onClose={() => setShowMediaPlayer(false)}
          />
        </div>
      )}

      {/* Smart Window Tiler & Desktop Macro Dashboard (WIN-01, MAC-01) */}
      {showWindowTiler && (
        <div style={{ position: 'absolute', bottom: 90, left: 24, zIndex: 120 }}>
          <WindowTilerHUD
            externalEvent={windowTilerExternalEvent}
            onClose={() => setShowWindowTiler(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Obsidian Cross-Vault Graph & Dev Canvas (KNG-02, UI-02) */}
      {showKnowledgeCanvas && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '920px', height: '620px', zIndex: 128 }}>
          <KnowledgeCanvasHUD
            externalEvent={knowledgeCanvasExternalEvent}
            onClose={() => setShowKnowledgeCanvas(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Multimodal Context Fusion & Visual-Semantic Grounding HUD (FUS-01, SAF-01) */}
      {showMultimodalFusion && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '920px', height: '620px', zIndex: 128 }}>
          <MultimodalFusionHUD
            externalEvent={multimodalFusionExternalEvent}
            onClose={() => setShowMultimodalFusion(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Autonomous Desktop Macro Synthesis & Self-Healing Workflow HUD (MAC-02, AUT-02) */}
      {showMacroWorkflow && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '920px', height: '620px', zIndex: 128 }}>
          <MacroWorkflowHUD
            externalEvent={macroWorkflowExternalEvent}
            onClose={() => setShowMacroWorkflow(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Advanced Bi-Directional Telegram Mobile Command Mesh HUD (TEL-04, REM-02) */}
      {showTelegramMesh && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '920px', height: '620px', zIndex: 128 }}>
          <TelegramMeshHUD
            externalEvent={telegramMeshExternalEvent}
            onClose={() => setShowTelegramMesh(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Adaptive Low-Latency Neural Voice & Proactive Persona Engine HUD (VOX-05, PER-02) */}
      {showAdaptiveVoice && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '920px', height: '620px', zIndex: 128 }}>
          <AdaptiveVoicePersonaHUD
            externalEvent={adaptiveVoiceExternalEvent}
            onClose={() => setShowAdaptiveVoice(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Dynamic DAG Swarm Task Orchestrator HUD (SWM-01, AUT-03) */}
      {showSwarmOrchestrator && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '960px', height: '640px', zIndex: 128 }}>
          <SwarmOrchestratorHUD
            externalEvent={swarmOrchestratorExternalEvent}
            onClose={() => setShowSwarmOrchestrator(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Temporal Intent Memory & Counterfactual Reasoning HUD (MEM-03, RSN-01) */}
      {showTemporalReasoning && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '920px', height: '620px', zIndex: 128 }}>
          <TemporalReasoningHUD
            externalEvent={temporalReasoningExternalEvent}
            onClose={() => setShowTemporalReasoning(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Multi-Display Spatial Holographic Canvas HUD (DSP-01, WIN-03) */}
      {showSpatialLayout && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '940px', height: '620px', zIndex: 128 }}>
          <SpatialLayoutHUD
            externalEvent={spatialLayoutExternalEvent}
            onClose={() => setShowSpatialLayout(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Proactive Ambient Intelligence & Contextual Notification Hub (AMB-02, NOT-02) */}
      {showAmbientIntelligence && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '920px', height: '620px', zIndex: 128 }}>
          <AmbientIntelligenceHUD
            externalEvent={ambientIntelligenceExternalEvent}
            onClose={() => setShowAmbientIntelligence(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Metacognitive Self-Reflection & Execution Calibration HUD (META-01, COG-01) */}
      {showMetacognitiveReflector && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '920px', height: '620px', zIndex: 128 }}>
          <MetacognitiveReflectorHUD
            externalEvent={metacognitiveReflectorExternalEvent}
            onClose={() => setShowMetacognitiveReflector(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Autonomous Local Fine-Tuning & Adaptive LoRA Adapter Hub HUD (ADA-01, MOD-02) */}
      {showLoRAAdapterHub && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '920px', height: '620px', zIndex: 128 }}>
          <LoRAAdapterHubHUD
            externalEvent={loraAdapterHubExternalEvent}
            onClose={() => setShowLoRAAdapterHub(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Spatial Cursor-Voice Intent Synapse HUD (VOX-07, GES-01) */}
      {showSpatialVoiceSynapse && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '840px', height: '620px', zIndex: 132 }}>
          <SpatialVoiceSynapseHUD
            externalEvent={spatialVoiceSynapseExternalEvent}
            onClose={() => setShowSpatialVoiceSynapse(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Predictive Resource Governor HUD (GOV-03, RES-02) */}
      {showResourceGovernor && (
        <ResourceGovernorHUD
          externalEvent={resourceGovernorExternalEvent}
          onClose={() => setShowResourceGovernor(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* GUI Semantic Grounding HUD (ACT-01, VIS-04) */}
      {showScreenGrounding && (
        <ScreenGroundingHUD
          externalEvent={screenGroundingExternalEvent}
          onClose={() => setShowScreenGrounding(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Declarative GUI Action Player HUD (ACT-02, EXEC-03) */}
      {showGuiActionPlayer && (
        <GuiActionPlayerHUD
          externalEvent={guiActionPlayerExternalEvent}
          onClose={() => setShowGuiActionPlayer(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Cross-App Workflow Orchestrator HUD (AUT-05, WIN-02) */}
      {showCrossAppWorkflow && (
        <CrossAppWorkflowHUD
          externalEvent={crossAppWorkflowExternalEvent}
          onClose={() => setShowCrossAppWorkflow(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Desktop Watchdog & Task Interceptor HUD (DOG-01, INT-03) */}
      {showDesktopWatchdog && (
        <DesktopWatchdogHUD
          externalEvent={desktopWatchdogExternalEvent}
          onClose={() => setShowDesktopWatchdog(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Episodic Memory Consolidation HUD (MEM-06, ABS-01) */}
      {showMemoryConsolidation && (
        <MemoryConsolidationHUD
          externalEvent={memoryConsolidationExternalEvent}
          onClose={() => setShowMemoryConsolidation(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Epistemic Belief Network HUD (EPI-01, RES-03) */}
      {showEpistemicBeliefNetwork && (
        <EpistemicBeliefNetworkHUD
          externalEvent={epistemicBeliefNetworkExternalEvent}
          onClose={() => setShowEpistemicBeliefNetwork(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Contextual World-Model Simulator HUD (SIM-01, EVA-02) */}
      {showWorldModelSimulator && (
        <WorldModelSimulatorHUD
          externalEvent={worldModelSimulatorExternalEvent}
          onClose={() => setShowWorldModelSimulator(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Cognitive Load Balancer & Attentional Pacing HUD (COG-03, PAC-01) */}
      {showCognitiveLoadBalancer && (
        <CognitiveLoadBalancerHUD
          externalEvent={cognitiveLoadBalancerExternalEvent}
          onClose={() => setShowCognitiveLoadBalancer(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Agent Swarm Mesh & Specialist Registry HUD (MSH-01, AGT-04) */}
      {showAgentSwarmMesh && (
        <AgentSwarmMeshHUD
          externalEvent={agentSwarmMeshExternalEvent}
          onClose={() => setShowAgentSwarmMesh(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Task Auction & Capability Bidding HUD (AUC-01, BID-02) */}
      {showTaskAuctionProtocol && (
        <TaskAuctionProtocolHUD
          externalEvent={taskAuctionProtocolExternalEvent}
          onClose={() => setShowTaskAuctionProtocol(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Swarm State Consensus & CRDT HUD (CRDT-01, CON-04) */}
      {showSwarmConsensusCRDT && (
        <SwarmConsensusCRDTHUD
          externalEvent={swarmConsensusCRDTExternalEvent}
          onClose={() => setShowSwarmConsensusCRDT(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Byzantine Worker Watchdog & Failover Arbiter HUD (BYZ-01, ARB-02) */}
      {showSwarmWatchdogArbiter && (
        <SwarmWatchdogArbiterHUD
          externalEvent={swarmWatchdogArbiterExternalEvent}
          onClose={() => setShowSwarmWatchdogArbiter(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Goal Decomposition Tree HUD (GOAL-01, TREE-02) */}
      {showGoalDecompositionTree && (
        <GoalDecompositionTreeHUD
          externalEvent={goalDecompositionTreeExternalEvent}
          onClose={() => setShowGoalDecompositionTree(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Adaptive Branch Planner HUD (SPEC-01, PRUN-03) */}
      {showAdaptiveBranchPlanner && (
        <AdaptiveBranchPlannerHUD
          externalEvent={adaptiveBranchPlannerExternalEvent}
          onClose={() => setShowAdaptiveBranchPlanner(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Self-Healing Dynamic Workflow Orchestrator HUD (HEAL-01, ORCH-04) */}
      {showSelfHealingOrchestrator && (
        <SelfHealingOrchestratorHUD
          externalEvent={selfHealingOrchestratorExternalEvent}
          onClose={() => setShowSelfHealingOrchestrator(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Execution Stream Shield & Adaptive Persona HUD (STREAM-01, PERSONA-02) */}
      {showExecutionStreamShield && (
        <ExecutionStreamShieldHUD
          externalEvent={executionStreamShieldExternalEvent}
          onClose={() => setShowExecutionStreamShield(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Safety Tier Matrix & Pragmatic Auto-Execution HUD (TIER-01, AUTO-02) */}
      {showSafetyTierMatrix && (
        <SafetyTierMatrixHUD
          externalEvent={safetyTierMatrixExternalEvent}
          onClose={() => setShowSafetyTierMatrix(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Conversational Voice Confirmation HUD (VOICE-01, CONFIRM-03) */}
      {showVoiceConfirmation && (
        <VoiceConfirmationHUD
          externalEvent={voiceConfirmationExternalEvent}
          onClose={() => setShowVoiceConfirmation(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Silent Activity Monitor & Background Telemetry HUD (HUD-01, MON-04) */}
      {showSilentActivityMonitor && (
        <SilentActivityMonitorHUD
          externalEvent={silentActivityMonitorExternalEvent}
          onClose={() => setShowSilentActivityMonitor(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Real-Time Screen Intelligence & Visual Task Tracker HUD (VIS-01, OCR-02) */}
      {showScreenIntelligence && (
        <ScreenIntelligenceHUD
          onClose={() => setShowScreenIntelligence(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Autonomous Multi-Agent Local Swarm Engine HUD (SWARM-01, AGENT-02) */}
      {showMultiAgentSwarm && (
        <MultiAgentSwarmHUD
          onClose={() => setShowMultiAgentSwarm(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Full-Duplex Conversational Voice & Acoustic Barge-In HUD (VOICE-01, BARGE-02) */}
      {showFullDuplexVoice && (
        <FullDuplexVoiceHUD
          onClose={() => setShowFullDuplexVoice(false)}
          sendMessage={(msg) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify(msg));
            }
          }}
        />
      )}

      {/* Dynamic Micro-Sandbox & AST Jail HUD (SEC-04, ENV-02) */}
      {showSandboxExecutionJail && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '840px', height: '620px', zIndex: 131 }}>
          <SandboxExecutionJailHUD
            externalEvent={sandboxExecutionJailExternalEvent}
            onClose={() => setShowSandboxExecutionJail(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Autonomous Self-Healing Kernel HUD (HEAL-01, SYM-02) */}
      {showSelfHealingKernel && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '840px', height: '620px', zIndex: 130 }}>
          <SelfHealingKernelHUD
            externalEvent={selfHealingKernelExternalEvent}
            onClose={() => setShowSelfHealingKernel(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Predictive Task Anticipation & Ambient Pipelining HUD (PRED-01, AUT-04) */}
      {showPredictiveTaskHub && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '800px', height: '620px', zIndex: 129 }}>
          <PredictiveTaskHubHUD
            externalEvent={predictiveTaskHubExternalEvent}
            onClose={() => setShowPredictiveTaskHub(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Cross-Modal Conversational Workspace Synapse HUD (SYN-01, VOX-06) */}
      {showVoiceCodeSynapse && (
        <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', width: '920px', height: '620px', zIndex: 128 }}>
          <VoiceCodeSynapseHUD
            externalEvent={voiceCodeSynapseExternalEvent}
            onClose={() => setShowVoiceCodeSynapse(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}




      {/* Voice Persona & Dynamic Prosody HUD (VOX-03) */}
      {showVoicePersona && (
        <div style={{ position: 'absolute', bottom: 90, right: showMediaPlayer ? 380 : 24, zIndex: 120 }}>
          <VoicePersonaHUD
            externalEvent={voicePersonaExternalEvent}
            onClose={() => setShowVoicePersona(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Multi-App Context Fusion HUD (CTX-01) */}
      {showContextStream && (
        <div style={{ position: 'absolute', bottom: 90, left: showWindowTiler ? 380 : 24, zIndex: 120 }}>
          <ContextStreamHUD
            externalEvent={contextStreamExternalEvent}
            onClose={() => setShowContextStream(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Telegram Mobile Super-Companion HUD (TEL-02) */}
      {showTelegramCompanion && (
        <div style={{ position: 'absolute', bottom: 90, right: 340, zIndex: 125 }}>
          <TelegramCompanionHUD
            externalEvent={telegramCompanionExternalEvent}
            onClose={() => setShowTelegramCompanion(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Autonomous Document Synthesis HUD (DOC-01, KNG-01) */}
      {showDocumentSynthesis && (
        <div style={{ position: 'absolute', top: 80, right: 24, zIndex: 125 }}>
          <DocumentSynthesisHUD
            externalEvent={documentSynthesisExternalEvent}
            onClose={() => setShowDocumentSynthesis(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* AST Code Intelligence & Symbol HUD (DEV-01) */}
      {showWorkspaceCode && (
        <div style={{ position: 'absolute', top: 90, left: 340, zIndex: 126 }}>
          <WorkspaceCodeHUD
            externalEvent={workspaceCodeExternalEvent}
            onClose={() => setShowWorkspaceCode(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Deep Associative Long-Term Memory HUD (MEM-02, VEC-01) */}
      {showAssociativeMemory && (
        <div style={{ position: 'absolute', top: 90, right: 340, zIndex: 125 }}>
          <AssociativeMemoryHUD
            externalEvent={associativeMemoryExternalEvent}
            onClose={() => setShowAssociativeMemory(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Autonomous Proactive Scheduler HUD (SCH-02, AUT-01) */}
      {showProactiveScheduler && (
        <div style={{ position: 'absolute', bottom: 90, left: 340, zIndex: 125 }}>
          <ProactiveSchedulerHUD
            externalEvent={proactiveSchedulerExternalEvent}
            onClose={() => setShowProactiveScheduler(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Multimodal Screen Vision Viewport HUD (VIS-01, GUI-01) */}
      {showScreenVision && (
        <div style={{ position: 'absolute', top: 90, left: 24, zIndex: 125 }}>
          <ScreenVisionHUD
            externalEvent={screenVisionExternalEvent}
            onClose={() => setShowScreenVision(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Sovereign Autonomous Browser Operator HUD (WEB-02, RES-01) */}
      {showBrowserOperator && (
        <div style={{ position: 'absolute', top: 80, left: 24, zIndex: 125 }}>
          <BrowserOperatorHUD
            externalEvent={browserOperatorExternalEvent}
            onClose={() => setShowBrowserOperator(false)}
            sendMessage={(msg) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(msg));
              }
            }}
          />
        </div>
      )}

      {/* Sound-Reactive 3D Particle Orb HUD (VOX-04, ORB-02) */}
      {showParticleOrb && (
        <div style={{ position: 'absolute', top: 80, right: 24, zIndex: 126 }}>
          <ParticleOrbHUD
            onClose={() => setShowParticleOrb(false)}
            onSendIntent={(intent) => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: 'prompt', payload: { text: intent } }));
              }
            }}
          />
        </div>
      )}

      {/* Mini Overlay Widget (Phase 5) */}

      {showMiniOverlay && (

        <MiniOverlay

          orbState={orbState}

          currentMode={currentMode}

          nextScheduledItem={scheduledJobs.length > 0 ? scheduledJobs[0] : null}

          currentTaskName={isStreaming ? 'Replying' : orbState === 'thinking' ? 'Reasoning' : undefined}

          onCycleMode={handleCycleMode}

          onTriggerKillswitch={handleTriggerKillswitch}

          onResume={handleResume}

          onClose={() => setShowMiniOverlay(false)}

        />

      )}



      {/* Slide-In Side Panel Drawer */}

      <div

        style={{

          position: 'absolute',

          top: 60,

          right: 0,

          bottom: 0,

          width: 440,

          background: 'rgba(8, 11, 16, 0.96)',

          backdropFilter: 'blur(20px)',

          borderLeft: '1px solid rgba(0, 82, 255, 0.35)',

          padding: 24,

          boxShadow: '-8px 0 32px rgba(0, 82, 255, 0.15), -2px 0 10px rgba(0, 0, 0, 0.8)',

          transform: isPanelOpen ? 'translateX(0)' : 'translateX(100%)',

          transition: 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)',

          zIndex: 25

        }}

      >

        {activePanel === 'dashboard' && (

          <DashboardPanel

            onClose={() => setActivePanel(null)}

            onSendWs={handleSendWs}

            scheduledJobs={scheduledJobs}

            watchlistItems={watchlistItems}

          />

        )}

        {activePanel === 'history' && (

          <HistoryPanel onClose={() => setActivePanel(null)} messages={historyMessages} />

        )}

        {activePanel === 'action_log' && (

          <ActionLogPanel onClose={() => setActivePanel(null)} />

        )}

        {activePanel === 'rules' && (

          <LearnedRulesPanel

            onClose={() => setActivePanel(null)}

            rules={learnedRules}

            onDeleteRule={handleDeleteRule}

            onEditRule={handleEditRule}

          />

        )}

        {activePanel === 'approvals' && (

          <ApprovalsPanel onClose={() => setActivePanel(null)} />

        )}

        {activePanel === 'settings' && (

          <SettingsPanel

            onClose={() => setActivePanel(null)}

            hotkeys={hotkeys}

            onUpdateHotkey={handleUpdateHotkey}

            hotkeyError={hotkeyError}

            wakePhrase={wakePhrase}

            onSetWakePhrase={handleSetWakePhrase}

            isMuted={isMuted}

            onToggleMute={handleToggleMute}

          />

        )}

        {activePanel === 'live_view' && (

          <LiveViewPanel

            onClose={() => setActivePanel(null)}

            liveFrame={liveFrame}

            takeoverPrompt={takeoverPrompt}

            onTakeoverDecision={handleTakeoverDecision}

          />

        )}

      </div>



      {/* Screen Control Safety Overlay with Neon Amber/Emerald/Ruby Border & Action Ticker */}

      <ScreenBorderOverlay

        overlayState={screenOverlayState}

        clickTarget={clickTarget}

        tickerItems={tickerItems}

        annotations={hudAnnotations}

        ambientAlerts={ambientAlerts}

        onDismissAlert={(id) => setAmbientAlerts((prev) => prev.filter((a) => a.id !== id))}

        onResumeAutomation={() => handleTakeoverDecision('continue')}

        onStopAutomation={() => handleTakeoverDecision('stop')}

      />



      {/* Raycast / Spotlight Centered Command Palette (Alt+Space) */}

      <CommandPalette

        isOpen={isCommandPaletteOpen}

        onClose={() => setIsCommandPaletteOpen(false)}

        commands={paletteCommands}

        onSubmitQuery={(q) => {

          setIsCommandPaletteOpen(false);

          handleSendMessage(q);

        }}

      />



      {/* Collapsible Streaming Terminal Console Drawer */}

      <StreamingConsole

        isOpen={isConsoleOpen}

        onToggle={() => setIsConsoleOpen((prev) => !prev)}

        lines={consoleLines}

        onClear={() => setConsoleLines([])}

      />



      {/* Floating HUD Card for Action Approvals and Diff Reviews */}

      {activeHudCard && (

        <HUDCard

          {...activeHudCard}

          onClose={() => setActiveHudCard(null)}

        />

      )}

      {/* Cyber HUD Floating Human Takeover Alert Banner */}
      {takeoverPayload && (
        <div style={{ position: 'fixed', top: 56, left: '50%', transform: 'translateX(-50%)', zIndex: 10000, width: '92%', maxWidth: 640 }}>
          <HumanTakeoverBanner
            prompt={takeoverPayload}
            onDecision={handleTakeoverDecision}
            onDismiss={() => setTakeoverPayload(null)}
          />
        </div>
      )}

    </div>

  );

};



export default App;

