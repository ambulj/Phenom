import React from 'react';
import { Button, Badge } from '@fluentui/react-components';
import {
  DismissRegular,
  PlayRegular,
  PauseRegular,
  HandRightRegular,
  StopRegular,
  EyeRegular,
  TargetRegular
} from '@fluentui/react-icons';

export interface AutomationStep {
  step_number: number;
  action: string;
  target: string;
  status: 'done' | 'current' | 'upcoming';
  result?: string;
}

interface LiveViewPanelProps {
  onClose: () => void;
  liveFrame?: string | null;
  takeoverPrompt?: string | null;
  onTakeoverDecision?: (decision: 'continue' | 'stop') => void;
  onPause?: () => void;
  onResume?: () => void;
  isPaused?: boolean;
  steps?: AutomationStep[];
  clickTarget?: { x: number; y: number } | null;
  missionTitle?: string | null;
  elapsedSeconds?: number;
  totalSteps?: number;
  completedSteps?: number;
}

export const LiveViewPanel: React.FC<LiveViewPanelProps> = ({
  onClose,
  liveFrame,
  takeoverPrompt,
  onTakeoverDecision,
  onPause,
  onResume,
  isPaused = false,
  steps = [],
  clickTarget,
  missionTitle,
  elapsedSeconds = 0,
  totalSteps = 0,
  completedSteps = 0
}) => {
  const percentComplete = totalSteps > 0 ? Math.min(100, Math.round((completedSteps / totalSteps) * 100)) : 0;
  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  const timerStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', color: '#f8fafc' }}>
      {/* Header with Close and Controls */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: 14,
          borderBottom: '1px solid rgba(0, 229, 255, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <EyeRegular style={{ color: '#00e5ff', fontSize: 20 }} />
          <h2 style={{ fontSize: 16, fontWeight: 700, color: '#f8fafc', margin: 0, letterSpacing: '0.4px' }}>
            Live Screen & Automation HUD
          </h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {/* Explicit Pause / Resume Button (Task 6E.4) */}
          <Button
            appearance="subtle"
            size="small"
            icon={isPaused ? <PlayRegular /> : <PauseRegular />}
            style={{
              color: isPaused ? '#ccff00' : '#00e5ff',
              background: 'rgba(0, 229, 255, 0.12)',
              border: '1px solid rgba(0, 229, 255, 0.3)',
              borderRadius: 6
            }}
            onClick={() => (isPaused ? onResume?.() : onPause?.())}
            title={isPaused ? 'Resume Automation' : 'Pause Automation'}
          >
            {isPaused ? 'Resume' : 'Pause'}
          </Button>

          {/* Explicit Take-Over Button (Task 6E.4) */}
          <Button
            appearance="subtle"
            size="small"
            icon={<HandRightRegular />}
            style={{
              color: '#f87171',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 6
            }}
            onClick={() => onTakeoverDecision?.('stop')}
            title="Instant Human Take-Over (Halts Automation)"
          >
            Take-Over
          </Button>

          <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingTop: 14, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Active Mission Telemetry Banner */}
        {missionTitle && (
          <div
            style={{
              background: 'linear-gradient(135deg, rgba(0, 229, 255, 0.08) 0%, rgba(13, 20, 36, 0.95) 100%)',
              border: '1px solid rgba(0, 229, 255, 0.35)',
              borderRadius: 8,
              padding: 12,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
                🎯 {missionTitle}
              </span>
              <span style={{ fontSize: 12, fontFamily: 'Consolas, monospace', color: '#00e5ff', fontWeight: 600 }}>
                ⏱️ {timerStr}
              </span>
            </div>

            {totalSteps > 0 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>
                  <span>Progress: {completedSteps}/{totalSteps} steps completed</span>
                  <span>{percentComplete}%</span>
                </div>
                <div style={{ width: '100%', height: 6, background: 'rgba(255, 255, 255, 0.1)', borderRadius: 3, overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${percentComplete}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #00e5ff, #0052ff)',
                      transition: 'width 0.3s ease'
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Human Takeover Alert Banner */}
        {takeoverPrompt && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.18)',
              border: '1px solid #ef4444',
              borderRadius: 8,
              padding: 12,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              boxShadow: '0 0 16px rgba(239, 68, 68, 0.3)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Badge appearance="filled" color="danger">HUMAN TAKEOVER DETECTED</Badge>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#fca5a5' }}>
                Automation Paused Immediately
              </span>
            </div>
            <p style={{ fontSize: 12, color: '#f8fafc', margin: 0 }}>
              {takeoverPrompt}
            </p>
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <Button
                appearance="primary"
                size="small"
                icon={<PlayRegular />}
                style={{ background: '#0052ff', color: '#fff', border: 'none', fontWeight: 600 }}
                onClick={() => onTakeoverDecision?.('continue')}
              >
                Continue
              </Button>
              <Button
                appearance="primary"
                size="small"
                icon={<StopRegular />}
                style={{ background: '#ef4444', color: '#fff', border: 'none', fontWeight: 600 }}
                onClick={() => onTakeoverDecision?.('stop')}
              >
                Abort
              </Button>
            </div>
          </div>
        )}

        {/* Live Viewport Screen Stream with Click-Target Overlay (Task 6E.4) */}
        <div
          style={{
            background: '#04070d',
            borderRadius: 10,
            overflow: 'hidden',
            border: '1px solid rgba(0, 229, 255, 0.3)',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 6px 20px rgba(0, 0, 0, 0.7)'
          }}
        >
          <div
            style={{
              padding: '6px 12px',
              background: 'rgba(13, 20, 36, 0.95)',
              borderBottom: '1px solid rgba(0, 229, 255, 0.18)',
              fontSize: 11,
              fontWeight: 600,
              color: '#94a3b8',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <TargetRegular style={{ color: '#00e5ff', fontSize: 14 }} />
              <span>Viewport Surface Tracking</span>
            </div>
            <Badge
              appearance="filled"
              style={{
                background: liveFrame ? 'rgba(0, 229, 255, 0.2)' : 'rgba(148, 163, 184, 0.1)',
                color: liveFrame ? '#00e5ff' : '#94a3b8',
                border: `1px solid ${liveFrame ? '#00e5ff' : 'rgba(148, 163, 184, 0.2)'}`,
                fontSize: 10
              }}
              size="small"
            >
              {isPaused ? 'PAUSED' : liveFrame ? 'STREAMING' : 'IDLE'}
            </Badge>
          </div>

          <div
            style={{
              width: '100%',
              height: 220,
              background: '#020408',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
              overflow: 'hidden'
            }}
          >
            {liveFrame ? (
              <img
                src={`data:image/jpeg;base64,${liveFrame}`}
                alt="Live automation viewport"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <span style={{ fontSize: 12, color: '#64748b' }}>
                No active automation session. Actions will stream in real-time.
              </span>
            )}

            {/* Click-Target Box Overlay (Task 6E.4) */}
            {clickTarget && (
              <div
                style={{
                  position: 'absolute',
                  left: `${clickTarget.x}%`,
                  top: `${clickTarget.y}%`,
                  width: 32,
                  height: 32,
                  border: '2px solid #00e5ff',
                  borderRadius: 6,
                  transform: 'translate(-50%, -50%)',
                  boxShadow: '0 0 16px #00e5ff, inset 0 0 8px rgba(0, 229, 255, 0.5)',
                  pointerEvents: 'none',
                  animation: 'pulse 1s infinite'
                }}
                title="Next Click Target"
              />
            )}
          </div>
        </div>

        {/* Step List: Done / Doing / Next (Task 6E.4) */}
        <div
          style={{
            background: 'rgba(8, 15, 28, 0.85)',
            border: '1px solid rgba(0, 229, 255, 0.2)',
            padding: 12,
            borderRadius: 10,
            boxShadow: '0 2px 10px rgba(0, 0, 0, 0.4)'
          }}
        >
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#00e5ff', marginBottom: 10, letterSpacing: '0.4px' }}>
            EXECUTION STEP LIST (DONE / DOING / NEXT)
          </h3>
          {steps.length === 0 ? (
            <div style={{ fontSize: 12, color: '#94a3b8' }}>
              No automation steps running. Task progress appears here in real-time.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {steps.map((st, i) => {
                const isCurrent = st.status === 'current';
                const isDone = st.status === 'done';
                return (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 10px',
                      borderRadius: 6,
                      background: isCurrent
                        ? 'rgba(0, 229, 255, 0.15)'
                        : isDone
                        ? 'rgba(204, 255, 0, 0.08)'
                        : 'rgba(4, 7, 13, 0.6)',
                      border: isCurrent
                        ? '1px solid #00e5ff'
                        : isDone
                        ? '1px solid rgba(204, 255, 0, 0.25)'
                        : '1px solid rgba(255, 255, 255, 0.08)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          color: isCurrent ? '#00e5ff' : isDone ? '#ccff00' : '#64748b',
                          fontFamily: 'Consolas, monospace'
                        }}
                      >
                        #{st.step_number}
                      </span>
                      <span style={{ fontSize: 12, color: isCurrent ? '#f8fafc' : isDone ? '#94a3b8' : '#64748b' }}>
                        {st.action} <strong style={{ color: isCurrent ? '#00e5ff' : '#cbd5e1' }}>{st.target}</strong>
                      </span>
                    </div>
                    <Badge
                      appearance="tint"
                      style={{
                        background: isCurrent
                          ? 'rgba(0, 229, 255, 0.2)'
                          : isDone
                          ? 'rgba(204, 255, 0, 0.15)'
                          : 'rgba(148, 163, 184, 0.1)',
                        color: isCurrent ? '#00e5ff' : isDone ? '#ccff00' : '#94a3b8',
                        fontSize: 10,
                        fontWeight: 600
                      }}
                      size="small"
                    >
                      {isCurrent ? 'DOING' : isDone ? 'DONE' : 'NEXT'}
                    </Badge>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Safety Invariant Notice */}
        <div style={{ background: 'rgba(4, 7, 13, 0.7)', border: '1px solid rgba(0, 229, 255, 0.15)', padding: 10, borderRadius: 8 }}>
          <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>
            🛡️ <strong style={{ color: '#00e5ff' }}>Guardian Protected</strong>: Physical mouse or keyboard movements pause
            automation within 1 second. Resuming requires explicit operator confirmation.
          </div>
        </div>
      </div>
    </div>
  );
};
