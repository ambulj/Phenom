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
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <EyeRegular style={{ color: '#00e5ff', fontSize: 20 }} />
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>Automation Live View</h2>
        </div>
        <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Human Takeover Alert Banner */}
        {takeoverPrompt && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.25)',
              border: '2px solid #ef4444',
              borderRadius: 8,
              padding: 14,
              display: 'flex',
              flexDirection: 'column',
              gap: 10
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
                style={{ backgroundColor: '#10b981', color: '#fff' }}
                onClick={() => onTakeoverDecision && onTakeoverDecision('continue')}
              >
                Continue Automation
              </Button>
              <Button
                appearance="primary"
                icon={<StopRegular />}
                style={{ backgroundColor: '#ef4444', color: '#fff' }}
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
            background: 'rgba(0, 0, 0, 0.6)',
            borderRadius: 8,
            overflow: 'hidden',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          <div
            style={{
              padding: '8px 12px',
              background: 'rgba(15, 23, 42, 0.8)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              fontSize: 12,
              fontWeight: 500,
              color: '#94a3b8',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <span>Active Browser / Screen View</span>
            <Badge appearance="tint" color={liveFrame ? 'success' : 'subtle'} size="small">
              {liveFrame ? 'STREAMING' : 'IDLE'}
            </Badge>
          </div>
          <div
            style={{
              width: '100%',
              height: 220,
              background: '#090d16',
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
        <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 14, borderRadius: 8 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#60a5fa', marginBottom: 10 }}>
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
                        ? 'rgba(96, 165, 250, 0.2)'
                        : st.status === 'done'
                        ? 'rgba(16, 185, 129, 0.1)'
                        : 'rgba(15, 23, 42, 0.3)',
                    border:
                      st.status === 'current'
                        ? '1px solid #60a5fa'
                        : '1px solid rgba(255, 255, 255, 0.05)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#cbd5e1' }}>
                      #{st.step_number}
                    </span>
                    <span style={{ fontSize: 13, color: '#f8fafc' }}>
                      {st.action} <strong>{st.target}</strong>
                    </span>
                  </div>
                  <Badge
                    appearance="tint"
                    color={
                      st.status === 'done'
                        ? 'success'
                        : st.status === 'current'
                        ? 'informative'
                        : 'subtle'
                    }
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
        <div style={{ background: 'rgba(30, 41, 59, 0.3)', padding: 12, borderRadius: 8 }}>
          <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
            🔒 <strong>Safety Enforced</strong>: Payments and checkouts are blocked by construction.
            Human takeover pauses automation in under 1 second upon physical mouse or key movement.
          </div>
        </div>
      </div>
    </div>
  );
};
