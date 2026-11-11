import React, { useState } from 'react';
import {
  DismissRegular,
  AlertRegular,
  SendRegular,
  DocumentSearchRegular,
  ArrowCounterclockwiseRegular,
  SparkleRegular,
} from '@fluentui/react-icons';

interface AmbientNudgeUI {
  nudge_id: string;
  category: 'FOCUS' | 'CALENDAR' | 'MILESTONE' | 'SYSTEM';
  title: string;
  message: string;
  voice_phrase?: string;
  timestamp: string;
}

interface RemoteFileUI {
  file_name: string;
  relative_path: string;
  size_bytes: number;
}

interface AmbientCompanionHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const AmbientCompanionHUD: React.FC<AmbientCompanionHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [activeFocusApp, setActiveFocusApp] = useState<string>('Visual Studio Code - Phenom');
  const [primaryGoal] = useState<string>('Milestone 30 Multi-Agent Swarm & Full-Duplex Voice OS');
  const [cooldownSec, setCooldownSec] = useState<number>(300);
  const [searchQuery, setSearchQuery] = useState<string>('PLAN.md');
  const [searchResults, setSearchResults] = useState<RemoteFileUI[]>([
    { file_name: 'PLAN.md', relative_path: '.planning/phases/30-04-ambient-context-watchdog/PLAN.md', size_bytes: 3450 },
    { file_name: 'PLAN.md', relative_path: '.planning/phases/30-03-full-duplex-voice/PLAN.md', size_bytes: 4120 },
  ]);

  const [nudges, setNudges] = useState<AmbientNudgeUI[]>([
    {
      nudge_id: 'nudge-1',
      category: 'FOCUS',
      title: 'Focus Drift Detected',
      message: 'Active window shifted to YouTube while objective is Milestone 30.',
      voice_phrase: "Bro, let's keep momentum on Milestone 30!",
      timestamp: '14:38:12',
    },
    {
      nudge_id: 'nudge-2',
      category: 'CALENDAR',
      title: 'Upcoming Sprint Sync',
      message: 'Milestone 30 Architecture Review starts in 10 minutes.',
      voice_phrase: 'Hey bro, sprint review starts in 10 minutes.',
      timestamp: '14:40:00',
    },
  ]);

  const [voiceNotes, setVoiceNotes] = useState<Array<{ id: string; user: string; text: string; reply: string }>>([
    {
      id: 'vn-1',
      user: 'Primary Operator',
      text: 'Send me the latest plan file for milestone 30',
      reply: 'Haan bro! Retrieved PLAN.md from workspace. File sent securely.',
    },
  ]);

  const handleTriggerFocusNudge = () => {
    const newNudge: AmbientNudgeUI = {
      nudge_id: `nudge-${Date.now()}`,
      category: 'FOCUS',
      title: 'Manual Focus Nudge',
      message: `Active objective: ${primaryGoal}. Focused application: ${activeFocusApp}`,
      voice_phrase: `Bro, staying locked into ${primaryGoal}!`,
      timestamp: new Date().toLocaleTimeString(),
    };
    setNudges((prev) => [newNudge, ...prev.slice(0, 9)]);
  };

  const handleSimulateRemoteVoiceNote = () => {
    const newVn = {
      id: `vn-${Date.now()}`,
      user: 'Mobile Telegram Client',
      text: 'What is the status of the local multi-agent swarm engine?',
      reply: 'Swarm active: 3 subagents (Coder, Research, Executive) nominal.',
    };
    setVoiceNotes((prev) => [newVn, ...prev.slice(0, 4)]);
  };

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'FOCUS':
        return '#00e5ff'; // Cyan
      case 'CALENDAR':
        return '#ffd600'; // Amber
      case 'MILESTONE':
        return '#d500f9'; // Magenta
      default:
        return '#00e676'; // Green
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(8, 10, 18, 0.88)',
        backdropFilter: 'blur(16px)',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
        color: '#e0e0e0',
        padding: '24px',
        boxSizing: 'border-box',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid rgba(0, 229, 255, 0.25)',
          paddingBottom: '16px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <SparkleRegular style={{ fontSize: '28px', color: '#00e5ff' }} />
          <div>
            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600, letterSpacing: '0.5px' }}>
              AMBIENT CONTEXT WATCHDOG & TELEGRAM SUPER-COMPANION v2
            </h2>
            <div style={{ fontSize: '12px', color: '#888', marginTop: '4px' }}>
              Proactive Ambient HUD Toasts • Focus Drift Nudges • Remote Voice Notes & Desktop File Retrieval
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span
            style={{
              padding: '4px 10px',
              borderRadius: '12px',
              backgroundColor: 'rgba(0, 230, 118, 0.15)',
              border: '1px solid rgba(0, 230, 118, 0.4)',
              color: '#00e676',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            RULE 4 LOCAL
          </span>
          <span
            style={{
              padding: '4px 10px',
              borderRadius: '12px',
              backgroundColor: 'rgba(0, 229, 255, 0.15)',
              border: '1px solid rgba(0, 229, 255, 0.4)',
              color: '#00e5ff',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            TELEGRAM MESH
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#aaa',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: '6px',
            }}
          >
            <DismissRegular style={{ fontSize: '20px' }} />
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', flex: 1, minHeight: 0 }}>
        {/* Left Column: Context Watchdog */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Active Goal & Focus Banner */}
          <div
            style={{
              padding: '16px 20px',
              backgroundColor: 'rgba(16, 20, 32, 0.6)',
              borderRadius: '8px',
              border: '1px solid rgba(0, 229, 255, 0.3)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#888', textTransform: 'uppercase' }}>
                Active Sprint Objective
              </span>
              <span style={{ fontSize: '11px', color: '#00e676', fontWeight: 600 }}>
                ● MONITORING
              </span>
            </div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: '#00e5ff' }}>
              {primaryGoal}
            </div>
            <div style={{ fontSize: '12px', color: '#aaa', marginTop: '4px' }}>
              Focused App: <strong style={{ color: '#fff' }}>{activeFocusApp}</strong>
            </div>
          </div>

          {/* Quick Actions */}
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleTriggerFocusNudge}
              style={{
                flex: 1,
                padding: '10px 16px',
                borderRadius: '6px',
                backgroundColor: 'rgba(0, 229, 255, 0.15)',
                border: '1px solid #00e5ff',
                color: '#fff',
                cursor: 'pointer',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              <AlertRegular />
              Trigger Context Nudge
            </button>
            <button
              onClick={() => setActiveFocusApp(activeFocusApp.includes('Code') ? 'Google Chrome - YouTube' : 'Visual Studio Code - Phenom')}
              style={{
                padding: '10px 16px',
                borderRadius: '6px',
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#aaa',
                cursor: 'pointer',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <ArrowCounterclockwiseRegular />
              Switch App
            </button>
          </div>

          {/* Ambient Toasts Waterfall */}
          <div
            style={{
              flex: 1,
              backgroundColor: 'rgba(16, 20, 32, 0.5)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
            }}
          >
            <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '12px', color: '#00e5ff' }}>
              Recent Ambient Toasts & Nudges
            </div>
            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {nudges.map((nudge) => (
                <div
                  key={nudge.nudge_id}
                  style={{
                    padding: '10px 14px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    borderLeft: `3px solid ${getCategoryColor(nudge.category)}`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 700,
                          padding: '2px 6px',
                          borderRadius: '4px',
                          backgroundColor: `${getCategoryColor(nudge.category)}22`,
                          color: getCategoryColor(nudge.category),
                        }}
                      >
                        {nudge.category}
                      </span>
                      <strong style={{ fontSize: '13px', color: '#fff' }}>{nudge.title}</strong>
                    </div>
                    <span style={{ fontSize: '11px', color: '#888' }}>{nudge.timestamp}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#bbb' }}>{nudge.message}</div>
                  {nudge.voice_phrase && (
                    <div style={{ fontSize: '11px', color: '#00e676', marginTop: '6px', fontStyle: 'italic' }}>
                      💬 "{nudge.voice_phrase}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Telegram Super-Companion */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Telegram Status Card */}
          <div
            style={{
              padding: '16px 20px',
              backgroundColor: 'rgba(16, 20, 32, 0.6)',
              borderRadius: '8px',
              border: '1px solid rgba(213, 0, 249, 0.3)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#888', textTransform: 'uppercase' }}>
                Telegram Super-Companion v2
              </span>
              <span style={{ fontSize: '11px', color: '#d500f9', fontWeight: 600 }}>
                ● UPLINK ACTIVE
              </span>
            </div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>
              Bi-Directional Voice Notes & Remote File Dispatch
            </div>
            <div style={{ fontSize: '11px', color: '#888' }}>
              Strict Rule 11 Security: .env, credentials & private keys filtered
            </div>
          </div>

          {/* Voice Notes Feed */}
          <div
            style={{
              backgroundColor: 'rgba(16, 20, 32, 0.5)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#d500f9' }}>
                Remote Voice Notes Feed
              </span>
              <button
                onClick={handleSimulateRemoteVoiceNote}
                style={{
                  padding: '4px 8px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(213, 0, 249, 0.2)',
                  border: '1px solid #d500f9',
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: '11px',
                }}
              >
                Simulate Voice Note
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '140px', overflowY: 'auto' }}>
              {voiceNotes.map((vn) => (
                <div
                  key={vn.id}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    borderLeft: '3px solid #d500f9',
                    fontSize: '12px',
                  }}
                >
                  <div style={{ color: '#aaa', fontSize: '11px' }}>From: {vn.user}</div>
                  <div style={{ color: '#fff', margin: '3px 0' }}>"{vn.text}"</div>
                  <div style={{ color: '#00e676', fontSize: '11px' }}>Reply: {vn.reply}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Remote Desktop File Search */}
          <div
            style={{
              flex: 1,
              backgroundColor: 'rgba(16, 20, 32, 0.5)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
              minHeight: 0,
            }}
          >
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#00e5ff', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <DocumentSearchRegular />
              Remote Desktop File Search
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search files..."
                style={{
                  flex: 1,
                  padding: '6px 10px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  color: '#fff',
                  fontSize: '12px',
                }}
              />
              <button
                onClick={() => {
                  setSearchResults([
                    { file_name: searchQuery, relative_path: `workspace/${searchQuery}`, size_bytes: 2048 },
                  ]);
                }}
                style={{
                  padding: '6px 12px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(0, 229, 255, 0.2)',
                  border: '1px solid #00e5ff',
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <SendRegular />
              </button>
            </div>

            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {searchResults.map((file, i) => (
                <div
                  key={i}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    fontSize: '11px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: '#fff' }}>{file.file_name}</div>
                    <div style={{ color: '#888', fontSize: '10px' }}>{file.relative_path}</div>
                  </div>
                  <span style={{ color: '#aaa' }}>{file.size_bytes} B</span>
                </div>
              ))}
            </div>
          </div>

          {/* Cooldown Settings */}
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: 'rgba(16, 20, 32, 0.5)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
              <span>Ambient Nudge Cooldown</span>
              <span>{cooldownSec} s</span>
            </div>
            <input
              type="range"
              min="60"
              max="900"
              step="30"
              value={cooldownSec}
              onChange={(e) => setCooldownSec(parseInt(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
