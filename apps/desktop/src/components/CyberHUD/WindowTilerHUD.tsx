import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  ArrowMaximizeRegular,
  ArrowMinimizeRegular,
  RecordRegular,
  RecordStopRegular,
  PlayRegular,
  DeleteRegular,
  TableSimpleRegular,
  DesktopRegular,
  AppFolderRegular,
} from '@fluentui/react-icons';

export interface WindowTilerHUDProps {
  onClose?: () => void;
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
}

interface SavedMacro {
  name: string;
  description: string;
  step_count: number;
  updated_at: number;
}

export const WindowTilerHUD: React.FC<WindowTilerHUDProps> = ({
  onClose,
  externalEvent,
  sendMessage,
}) => {
  const [activeTab, setActiveTab] = useState<'layouts' | 'macros'>('layouts');
  const [isMinimized, setIsMinimized] = useState<boolean>(false);
  const [activeLayout, setActiveLayout] = useState<string>('dev_mode');
  const [statusMessage, setStatusMessage] = useState<string>('Ready');

  // Macro recording state
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [activeRecordingName, setActiveRecordingName] = useState<string>('');
  const [newMacroName, setNewMacroName] = useState<string>('morning_routine');
  const [macros, setMacros] = useState<SavedMacro[]>([
    {
      name: 'morning_routine',
      description: 'Open Brave, Spotify, and terminal',
      step_count: 3,
      updated_at: Date.now() / 1000,
    },
    {
      name: 'deploy_check',
      description: 'Run build and open preview',
      step_count: 2,
      updated_at: Date.now() / 1000 - 3600,
    },
  ]);

  // Handle external WebSocket events
  useEffect(() => {
    if (!externalEvent) return;
    const { type, payload } = externalEvent;

    if (type === 'WINDOW_LAYOUT_APPLIED') {
      setActiveLayout(payload?.layout || 'custom');
      setStatusMessage(`Layout '${payload?.layout}' applied (${payload?.actions?.length || 0} windows)`);
    } else if (type === 'WINDOW_SNAPPED') {
      setStatusMessage(`Window snapped to ${payload?.zone}`);
    } else if (type === 'MACRO_RECORDING_STARTED') {
      setIsRecording(true);
      setActiveRecordingName(payload?.name || '');
      setStatusMessage(`Recording macro '${payload?.name}'...`);
    } else if (type === 'MACRO_RECORDING_STOPPED') {
      setIsRecording(false);
      setActiveRecordingName('');
      setStatusMessage(`Macro saved: ${payload?.name} (${payload?.step_count} steps)`);
      fetchMacros();
    } else if (type === 'MACRO_REPLAY_STARTED') {
      setStatusMessage(`Replaying macro '${payload?.name}'...`);
    } else if (type === 'MACRO_REPLAY_COMPLETED') {
      setStatusMessage(`Macro '${payload?.name}' completed in ${payload?.duration_ms}ms`);
    } else if (type === 'MACRO_REPLAY_HALTED') {
      setStatusMessage(`Replay halted by Guardian kill switch`);
    }
  }, [externalEvent]);

  // Helper to send backend tool execution request
  const triggerTool = (tool: string, args: Record<string, any>) => {
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: { tool, args },
      });
    }
  };

  const fetchMacros = () => {
    triggerTool('list_macros', {});
  };

  const handleApplyPreset = (presetName: string) => {
    setActiveLayout(presetName);
    setStatusMessage(`Applying ${presetName}...`);
    triggerTool('apply_window_layout', { layout_name: presetName });
  };

  const handleSnap = (zone: 'left' | 'right' | 'top' | 'bottom' | 'maximize' | 'center') => {
    setStatusMessage(`Snapping active window to ${zone}...`);
    triggerTool('snap_window', { snap_zone: zone });
  };

  const handleStartRecording = () => {
    const cleanName = newMacroName.trim().replace(/\s+/g, '_') || 'custom_macro';
    setIsRecording(true);
    setActiveRecordingName(cleanName);
    setStatusMessage(`Started recording '${cleanName}'...`);
    triggerTool('start_macro_recording', { name: cleanName });
  };

  const handleStopRecording = () => {
    setIsRecording(false);
    setStatusMessage('Saving macro...');
    triggerTool('stop_macro_recording', {});
  };

  const handleReplayMacro = (name: string) => {
    setStatusMessage(`Requesting replay for '${name}'...`);
    triggerTool('replay_macro', { name, speed: 1.0 });
  };

  const handleDeleteMacro = (name: string) => {
    setMacros((prev) => prev.filter((m) => m.name !== name));
    setStatusMessage(`Deleting '${name}'...`);
    triggerTool('delete_macro', { name });
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        width: isMinimized ? '320px' : '440px',
        zIndex: 9999,
        background: 'rgba(10, 16, 26, 0.92)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 240, 255, 0.35)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 24px rgba(0, 240, 255, 0.15)',
        borderRadius: '12px',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', system-ui, sans-serif",
        overflow: 'hidden',
        transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Title Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          background: 'rgba(0, 240, 255, 0.08)',
          borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <DesktopRegular style={{ color: '#00f0ff', fontSize: '18px' }} />
          <span
            style={{
              fontWeight: 700,
              fontSize: '13px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#00f0ff',
              textShadow: '0 0 8px rgba(0, 240, 255, 0.5)',
            }}
          >
            Window Tiler & Macro HUD
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
            }}
            title={isMinimized ? 'Expand' : 'Minimize'}
          >
            {isMinimized ? <ArrowMaximizeRegular /> : <ArrowMinimizeRegular />}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
              }}
              title="Close HUD"
            >
              <DismissRegular />
            </button>
          )}
        </div>
      </div>

      {!isMinimized && (
        <div style={{ padding: '14px' }}>
          {/* Tabs */}
          <div
            style={{
              display: 'flex',
              gap: '6px',
              marginBottom: '14px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              paddingBottom: '8px',
            }}
          >
            <button
              onClick={() => setActiveTab('layouts')}
              style={{
                flex: 1,
                padding: '6px 10px',
                borderRadius: '6px',
                border: activeTab === 'layouts' ? '1px solid #00f0ff' : '1px solid transparent',
                background: activeTab === 'layouts' ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                color: activeTab === 'layouts' ? '#00f0ff' : '#94a3b8',
                fontWeight: 600,
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
              }}
            >
              <TableSimpleRegular /> Workspace Layouts
            </button>
            <button
              onClick={() => setActiveTab('macros')}
              style={{
                flex: 1,
                padding: '6px 10px',
                borderRadius: '6px',
                border: activeTab === 'macros' ? '1px solid #00f0ff' : '1px solid transparent',
                background: activeTab === 'macros' ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                color: activeTab === 'macros' ? '#00f0ff' : '#94a3b8',
                fontWeight: 600,
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
              }}
            >
              <AppFolderRegular /> Desktop Macros
            </button>
          </div>

          {/* Tab 1: Layouts & Snapping */}
          {activeTab === 'layouts' && (
            <div>
              <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '8px', fontWeight: 600, textTransform: 'uppercase' }}>
                Preset Workspaces
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '14px' }}>
                {[
                  { id: 'dev_mode', label: 'Dev Mode', desc: 'Code 60% + Browser/Term' },
                  { id: 'research_mode', label: 'Research', desc: 'Browser 50% + Notes 50%' },
                  { id: 'chill_mode', label: 'Chill Mode', desc: 'Centered Media 60%x80%' },
                ].map((preset) => (
                  <button
                    key={preset.id}
                    onClick={() => handleApplyPreset(preset.id)}
                    style={{
                      padding: '10px 8px',
                      borderRadius: '8px',
                      border: activeLayout === preset.id ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.1)',
                      background: activeLayout === preset.id ? 'rgba(0, 240, 255, 0.18)' : 'rgba(255, 255, 255, 0.04)',
                      color: activeLayout === preset.id ? '#ffffff' : '#cbd5e1',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: '12px', marginBottom: '2px', color: activeLayout === preset.id ? '#00f0ff' : '#ffffff' }}>
                      {preset.label}
                    </div>
                    <div style={{ fontSize: '10px', color: '#94a3b8', lineHeight: 1.2 }}>{preset.desc}</div>
                  </button>
                ))}
              </div>

              <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '8px', fontWeight: 600, textTransform: 'uppercase' }}>
                Active Window Snapping
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '6px' }}>
                {[
                  { id: 'left', label: 'Left' },
                  { id: 'right', label: 'Right' },
                  { id: 'top', label: 'Top' },
                  { id: 'bottom', label: 'Bottom' },
                  { id: 'center', label: 'Center' },
                  { id: 'maximize', label: 'Max' },
                ].map((snap) => (
                  <button
                    key={snap.id}
                    onClick={() => handleSnap(snap.id as any)}
                    style={{
                      padding: '6px 4px',
                      borderRadius: '6px',
                      border: '1px solid rgba(0, 240, 255, 0.2)',
                      background: 'rgba(0, 240, 255, 0.06)',
                      color: '#00f0ff',
                      fontWeight: 600,
                      fontSize: '11px',
                      cursor: 'pointer',
                      textAlign: 'center',
                    }}
                  >
                    {snap.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Tab 2: Desktop Macros */}
          {activeTab === 'macros' && (
            <div>
              <div
                style={{
                  display: 'flex',
                  gap: '6px',
                  alignItems: 'center',
                  marginBottom: '12px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  padding: '8px',
                  borderRadius: '8px',
                }}
              >
                <input
                  type="text"
                  value={newMacroName}
                  onChange={(e) => setNewMacroName(e.target.value)}
                  placeholder="Macro name (e.g., morning_routine)"
                  disabled={isRecording}
                  style={{
                    flex: 1,
                    background: 'rgba(0, 0, 0, 0.4)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '6px',
                    padding: '6px 8px',
                    color: '#ffffff',
                    fontSize: '11px',
                    outline: 'none',
                  }}
                />
                {isRecording ? (
                  <button
                    onClick={handleStopRecording}
                    style={{
                      background: '#ef4444',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '6px 10px',
                      color: '#ffffff',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <RecordStopRegular /> Stop
                  </button>
                ) : (
                  <button
                    onClick={handleStartRecording}
                    style={{
                      background: '#00f0ff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '6px 10px',
                      color: '#0a101a',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <RecordRegular /> Record
                  </button>
                )}
              </div>

              {isRecording && (
                <div
                  style={{
                    padding: '8px',
                    marginBottom: '10px',
                    background: 'rgba(239, 68, 68, 0.15)',
                    border: '1px solid #ef4444',
                    borderRadius: '6px',
                    fontSize: '11px',
                    color: '#fca5a5',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <span
                    style={{
                      display: 'inline-block',
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: '#ef4444',
                      animation: 'pulse 1.5s infinite',
                    }}
                  />
                  Recording actions for: <strong>{activeRecordingName}</strong>
                </div>
              )}

              <div style={{ maxHeight: '160px', overflowY: 'auto' }}>
                {macros.map((m) => (
                  <div
                    key={m.name}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      background: 'rgba(255, 255, 255, 0.04)',
                      marginBottom: '6px',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '12px', color: '#00f0ff' }}>{m.name}</div>
                      <div style={{ fontSize: '10px', color: '#94a3b8' }}>
                        {m.step_count} steps &bull; {m.description}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        onClick={() => handleReplayMacro(m.name)}
                        style={{
                          background: 'rgba(0, 240, 255, 0.15)',
                          border: '1px solid #00f0ff',
                          borderRadius: '4px',
                          color: '#00f0ff',
                          cursor: 'pointer',
                          padding: '4px 8px',
                          fontSize: '11px',
                          fontWeight: 600,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <PlayRegular /> Run
                      </button>
                      <button
                        onClick={() => handleDeleteMacro(m.name)}
                        style={{
                          background: 'rgba(239, 68, 68, 0.1)',
                          border: '1px solid rgba(239, 68, 68, 0.4)',
                          borderRadius: '4px',
                          color: '#ef4444',
                          cursor: 'pointer',
                          padding: '4px 6px',
                          display: 'flex',
                        }}
                        title="Delete Macro"
                      >
                        <DeleteRegular />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Status Bar */}
          <div
            style={{
              marginTop: '12px',
              paddingTop: '8px',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '10px',
              color: '#64748b',
            }}
          >
            <span>Status: {statusMessage}</span>
            <span style={{ color: '#00f0ff' }}>Guardian SLA &lt;25ms</span>
          </div>
        </div>
      )}
    </div>
  );
};
