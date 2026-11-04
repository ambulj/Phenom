import React, { useState } from 'react';
import {
  PulseRegular,
  Speaker2Regular,
  ShieldCheckmarkRegular,
  PhoneLaptopRegular,
  DismissRegular,
} from '@fluentui/react-icons';
import {
  Win32EventPayload,
  WebRTCMirrorSessionPayload,
} from '../../types/protocol';

interface ProactiveFeedbackFabricProps {
  recentEvents: Win32EventPayload[];
  activeSessions: WebRTCMirrorSessionPayload[];
  totalScrubbed?: number;
  onPlayCue?: (cueType: string, spatialPan?: number) => void;
  onDisconnectWebRTC?: (sessionId: string) => void;
}

export const ProactiveFeedbackFabric: React.FC<ProactiveFeedbackFabricProps> = ({
  recentEvents,
  activeSessions,
  totalScrubbed = 0,
  onPlayCue,
  onDisconnectWebRTC,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);

  const getEventBadgeColor = (type: Win32EventPayload['event_type']) => {
    switch (type) {
      case 'WINDOW_CRASH':
      case 'EXCEPTION_DIALOG':
        return '#ff3366';
      case 'TERMINAL_ERROR_CODE':
        return '#ffb800';
      case 'BACKGROUND_MILESTONE':
        return '#00ffcc';
      case 'FOCUS_CHANGE':
        return '#80b8ff';
      case 'SYSTEM_ALERT':
      default:
        return '#bd93f9';
    }
  };

  return (
    <div
      style={{
        background: 'rgba(10, 14, 26, 0.88)',
        border: '1px solid #bd93f944',
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(12px)',
        boxShadow: '0 2px 12px rgba(0,0,0,0.5)',
        transition: 'all 0.3s ease',
        maxWidth: 480,
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          paddingBottom: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <PulseRegular style={{ color: '#bd93f9', fontSize: 16 }} />
          <span style={{ fontWeight: 600, letterSpacing: 0.5, color: '#bd93f9' }}>
            PROACTIVE EVENT FABRIC
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              background: 'rgba(189, 147, 249, 0.2)',
              color: '#bd93f9',
              fontWeight: 'bold',
            }}
          >
            ACTIVE
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {/* Privacy badge */}
          <span
            title="Permanent Rule 11: Real-Time In-Memory Privacy Scrubbing"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 10,
              background: 'rgba(0, 255, 204, 0.12)',
              border: '1px solid #00ffcc44',
              color: '#00ffcc',
              padding: '2px 6px',
              borderRadius: 4,
            }}
          >
            <ShieldCheckmarkRegular style={{ fontSize: 12 }} />
            {totalScrubbed} SCRUBBED
          </span>

          <button
            onClick={() => setIsMinimized(!isMinimized)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: 11,
            }}
          >
            {isMinimized ? '▼' : '▲'}
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Ambient Audio Cue Triggers */}
          <div
            style={{
              background: 'rgba(0,0,0,0.25)',
              borderRadius: 6,
              padding: '8px 10px',
              marginBottom: 10,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Speaker2Regular style={{ fontSize: 13, color: '#bd93f9' }} /> AMBIENT CUES:
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              {onPlayCue && (
                <>
                  <button
                    onClick={() => onPlayCue('SUBTLE_CHIME', -0.5)}
                    style={{
                      background: 'rgba(189, 147, 249, 0.15)',
                      border: '1px solid #bd93f955',
                      color: '#bd93f9',
                      borderRadius: 4,
                      padding: '2px 6px',
                      cursor: 'pointer',
                      fontSize: 10,
                    }}
                  >
                    Chime (L)
                  </button>
                  <button
                    onClick={() => onPlayCue('MILESTONE_FANFARE', 0.0)}
                    style={{
                      background: 'rgba(0, 255, 204, 0.15)',
                      border: '1px solid #00ffcc55',
                      color: '#00ffcc',
                      borderRadius: 4,
                      padding: '2px 6px',
                      cursor: 'pointer',
                      fontSize: 10,
                    }}
                  >
                    Milestone
                  </button>
                  <button
                    onClick={() => onPlayCue('RISK_GATE_WARNING', 0.5)}
                    style={{
                      background: 'rgba(255, 184, 0, 0.15)',
                      border: '1px solid #ffb80055',
                      color: '#ffb800',
                      borderRadius: 4,
                      padding: '2px 6px',
                      cursor: 'pointer',
                      fontSize: 10,
                    }}
                  >
                    Alert (R)
                  </button>
                </>
              )}
            </div>
          </div>

          {/* WebRTC Active Mirror Streams */}
          {activeSessions.length > 0 && (
            <div
              style={{
                background: 'rgba(0, 180, 255, 0.1)',
                border: '1px solid #00b4ff44',
                borderRadius: 6,
                padding: '8px 10px',
                marginBottom: 10,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <PhoneLaptopRegular style={{ fontSize: 13 }} /> LOCAL WEBRTC MIRROR
                </span>
                <span style={{ fontSize: 9, color: '#00ffcc' }}>Wi-Fi ONLY</span>
              </div>
              {activeSessions.map((s) => (
                <div
                  key={s.session_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: 10,
                    color: '#94a3b8',
                    marginTop: 2,
                  }}
                >
                  <span>
                    Device: {s.device_id} ({s.resolution} @ {s.fps_target}fps)
                  </span>
                  {onDisconnectWebRTC && (
                    <button
                      onClick={() => onDisconnectWebRTC(s.session_id)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#ff3366',
                        cursor: 'pointer',
                        padding: 0,
                      }}
                    >
                      <DismissRegular style={{ fontSize: 12 }} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Recent Event Feed */}
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>
            RECENT SYSTEM CONTEXT EVENTS ({recentEvents.length}):
          </div>

          {recentEvents.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '16px 0',
                color: '#64748b',
                fontStyle: 'italic',
                fontSize: 11,
              }}
            >
              No system context events recorded.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 200, overflowY: 'auto' }}>
              {recentEvents.slice(-8).reverse().map((ev) => {
                const color = getEventBadgeColor(ev.event_type);
                return (
                  <div
                    key={ev.event_id}
                    style={{
                      background: 'rgba(15, 23, 42, 0.65)',
                      border: `1px solid ${color}33`,
                      borderLeft: `3px solid ${color}`,
                      borderRadius: 4,
                      padding: '6px 8px',
                      fontSize: 11,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                      <span style={{ fontWeight: 600, color, fontSize: 10 }}>{ev.event_type}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        {ev.is_scrubbed && (
                          <span
                            style={{
                              fontSize: 8,
                              padding: '1px 3px',
                              borderRadius: 2,
                              background: 'rgba(0, 255, 204, 0.2)',
                              color: '#00ffcc',
                            }}
                          >
                            SCRUBBED
                          </span>
                        )}
                        <span style={{ fontSize: 9, color: '#64748b' }}>{ev.process_name}</span>
                      </div>
                    </div>
                    {ev.window_title && (
                      <div style={{ color: '#cbd5e1', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {ev.window_title}
                      </div>
                    )}
                    {Object.keys(ev.details).length > 0 && (
                      <div style={{ color: '#64748b', fontSize: 9, marginTop: 2 }}>
                        {JSON.stringify(ev.details)}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
};
