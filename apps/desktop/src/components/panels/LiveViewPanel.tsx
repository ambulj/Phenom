import React from 'react';
import { Button, Badge } from '@fluentui/react-components';
import { DismissRegular, PlayRegular, StopRegular, EyeRegular } from '@fluentui/react-icons';

interface AutomationStep {
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
  steps?: AutomationStep[];
}

export const LiveViewPanel: React.FC<LiveViewPanelProps> = ({
  onClose,
  liveFrame,
  takeoverPrompt,
  onTakeoverDecision,
  steps = []
}) => {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: 16,
          borderBottom: '1px solid rgba(0, 82, 255, 0.25)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <EyeRegular style={{ color: '#0052FF', fontSize: 20 }} />
          <h2 style={{ fontSize: 16, fontWeight: 600, color: '#f8fafc', margin: 0 }}>Automation Live View</h2>
        </div>
        <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Human Takeover Alert Banner */}
        {takeoverPrompt && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.20)',
              border: '2px solid #EF4444',
              borderRadius: 8,
              padding: 14,
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
              boxShadow: '0 0 15px rgba(239, 68, 68, 0.3)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Badge appearance="filled" color="danger">HUMAN TAKEOVER DETECTED</Badge>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#fca5a5' }}>
                Automation Paused Immediately
              </span>
            </div>
            <p style={{ fontSize: 12, color: '#f8fafc', margin: 0 }}>
              {takeoverPrompt} Please choose whether to resume or cancel automation:
            </p>
            <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
              <Button
                appearance="primary"
                icon={<PlayRegular />}
                style={{ background: 'linear-gradient(135deg, #0052FF, #1a66ff)', color: '#fff', fontWeight: 600, border: 'none' }}
                onClick={() => onTakeoverDecision && onTakeoverDecision('continue')}
              >
                Continue Automation
              </Button>
              <Button
                appearance="primary"
                icon={<StopRegular />}
                style={{ background: '#EF4444', color: '#fff', fontWeight: 600, border: 'none' }}
                onClick={() => onTakeoverDecision && onTakeoverDecision('stop')}
              >
                Stop / Abort
              </Button>
            </div>
          </div>
        )}

        {/* Live Viewport Screen Stream */}
        <div
          style={{
            background: '#040609',
            borderRadius: 8,
            overflow: 'hidden',
            border: '1px solid rgba(0, 82, 255, 0.35)',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.6)'
          }}
        >
          <div
            style={{
              padding: '8px 12px',
              background: 'rgba(13, 17, 26, 0.90)',
              borderBottom: '1px solid rgba(0, 82, 255, 0.20)',
              fontSize: 12,
              fontWeight: 500,
              color: '#94a3b8',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <span>Active Browser / Screen View</span>
            <Badge
              appearance="filled"
              style={{
                background: liveFrame ? 'rgba(204, 255, 0, 0.2)' : 'rgba(148, 163, 184, 0.1)',
                color: liveFrame ? '#CCFF00' : '#94a3b8',
                border: `1px solid ${liveFrame ? '#CCFF00' : 'rgba(148, 163, 184, 0.2)'}`,
                fontSize: 10
              }}
              size="small"
            >
              {liveFrame ? 'STREAMING' : 'IDLE'}
            </Badge>
          </div>
          <div
            style={{
              width: '100%',
              height: 220,
              background: '#080B10',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative'
            }}
          >
            {liveFrame ? (
              <img
                src={`data:image/jpeg;base64,${liveFrame}`}
                alt="Live automation viewport"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <span style={{ fontSize: 13, color: '#64748b' }}>
                No active browser session. Launch an automation task to stream.
              </span>
            )}
          </div>
        </div>

        {/* Step List Overlay */}
        <div
          style={{
            background: 'rgba(13, 17, 26, 0.85)',
            border: '1px solid rgba(0, 82, 255, 0.22)',
            padding: 14,
            borderRadius: 8,
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
          }}
        >
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#CCFF00', marginBottom: 10 }}>
            Execution Step List
          </h3>
          {steps.length === 0 ? (
            <div style={{ fontSize: 12, color: '#94a3b8' }}>
              No automation steps running. Plans and progress will appear here in real-time.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {steps.map((st, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 10px',
                    borderRadius: 6,
                    background:
                      st.status === 'current'
                        ? 'rgba(0, 82, 255, 0.25)'
                        : st.status === 'done'
                        ? 'rgba(204, 255, 0, 0.10)'
                        : 'rgba(8, 11, 16, 0.5)',
                    border:
                      st.status === 'current'
                        ? '1px solid #0052FF'
                        : '1px solid rgba(0, 82, 255, 0.15)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#0052FF', fontFamily: 'Consolas, monospace' }}>
                      #{st.step_number}
                    </span>
                    <span style={{ fontSize: 13, color: '#f8fafc' }}>
                      {st.action} <strong>{st.target}</strong>
                    </span>
                  </div>
                  <Badge
                    appearance="tint"
                    style={{
                      background: st.status === 'done' ? 'rgba(204, 255, 0, 0.15)' : st.status === 'current' ? 'rgba(0, 82, 255, 0.25)' : 'rgba(148, 163, 184, 0.1)',
                      color: st.status === 'done' ? '#CCFF00' : st.status === 'current' ? '#337aff' : '#94a3b8'
                    }}
                    size="small"
                  >
                    {st.status.toUpperCase()}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Safety Guarantees Notice */}
        <div style={{ background: 'rgba(8, 11, 16, 0.6)', border: '1px solid rgba(0, 82, 255, 0.15)', padding: 12, borderRadius: 8 }}>
          <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
            🔒 <strong style={{ color: '#CCFF00' }}>Safety Enforced</strong>: Payments and checkouts are blocked by construction.
            Human takeover pauses automation in under 1 second upon physical mouse or key movement.
          </div>
        </div>
      </div>
    </div>
  );
};
