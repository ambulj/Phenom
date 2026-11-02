import React, { useState, useEffect, useRef } from 'react';
import { HeaderBar } from './components/HeaderBar';
import { Orb, OrbQualityLevel } from './components/Orb';
import { ChatBox } from './components/ChatBox';
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
import { ScreenBorderOverlay, ScreenOverlayState, ClickTarget, TickerItem } from './components/ScreenBorderOverlay';
import { OrbState, ConfirmRequestPayload, LearnedRuleItem } from './types/protocol';
import { CommandPalette, CommandItem } from './components/CommandPalette';
import { HUDCard, HUDCardProps } from './components/HUDCard';
import { StreamingConsole, ConsoleLine } from './components/StreamingConsole';

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
  const [screenOverlayState, setScreenOverlayState] = useState<ScreenOverlayState>({ state: 'idle' });
  const [clickTarget, setClickTarget] = useState<ClickTarget | null>(null);
  const [tickerItems, setTickerItems] = useState<TickerItem[]>([]);

  // Modes, Scheduler, & Watchlist State (Phase 5)
  const [currentMode, setCurrentMode] = useState<string>('work');
  const [scheduledJobs, setScheduledJobs] = useState<any[]>([]);
  const [watchlistItems, setWatchlistItems] = useState<any[]>([]);
  const [showMiniOverlay, setShowMiniOverlay] = useState<boolean>(true);

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
            if (payload.full_text) {
              setHistoryMessages((prev) => [
                ...prev,
                { id: `hist-${Date.now()}`, role: 'assistant', content: payload.full_text }
              ]);
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
          } else if (mtype === 'screen.action_ticker') {
            setTickerItems((prev) => [...prev.slice(-5), payload]);
          } else if (mtype === 'automation.takeover_prompt') {
            setTakeoverPrompt(payload.reason || 'User interaction detected during automation.');
            setActivePanel('live_view'); // Automatically surface the Live View with prompt
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
  const handleTakeoverDecision = (decision: 'continue' | 'stop') => {
    if (!wsRef.current) return;
    setTakeoverPrompt(null);
    wsRef.current.send(
      JSON.stringify({
        id: `takeover-reply-${Date.now()}`,
        type: 'automation.takeover_reply',
        ts: new Date().toISOString(),
        payload: { decision }
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
      />

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
          background: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(20px)',
          borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
          padding: 24,
          boxShadow: '-8px 0 32px rgba(0, 0, 0, 0.5)',
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
    </div>
  );
};

export default App;
