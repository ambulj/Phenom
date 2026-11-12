import React from 'react';
import {
  WarningRegular,
  PlayRegular,
  StopRegular,
  DismissRegular,
  DesktopRegular,
} from '@fluentui/react-icons';
import { AutomationTakeoverPromptPayload } from '../../types/protocol';

export interface HumanTakeoverBannerProps {
  prompt: AutomationTakeoverPromptPayload;
  onDecision: (decision: 'continue' | 'stop', sessionId?: string | null) => void;
  onDismiss?: () => void;
}

export const HumanTakeoverBanner: React.FC<HumanTakeoverBannerProps> = ({
  prompt,
  onDecision,
  onDismiss,
}) => {
  const { reason, session_id, app_name, timestamp } = prompt;

  return (
    <div
      style={{
        position: 'relative',
        background: 'linear-gradient(135deg, rgba(20, 15, 10, 0.95) 0%, rgba(35, 20, 10, 0.9) 100%)',
        border: '1.5px solid #FF8800',
        borderRadius: 10,
        padding: '16px 20px',
        boxShadow: '0 0 25px rgba(255, 136, 0, 0.35), inset 0 0 15px rgba(255, 136, 0, 0.1)',
        backdropFilter: 'blur(16px)',
        color: '#F8FAFC',
        fontFamily: "'Segoe UI', -apple-system, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        margin: '10px 0',
        animation: 'pulseGlow 2.5s infinite alternate ease-in-out',
      }}
    >
      {/* Top Header Row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: 'rgba(255, 136, 0, 0.2)',
              border: '1px solid #FF8800',
              boxShadow: '0 0 10px rgba(255, 136, 0, 0.5)',
            }}
          >
            <WarningRegular style={{ color: '#FF8800', fontSize: 20 }} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 800,
                  letterSpacing: '1px',
                  color: '#FF8800',
                  textTransform: 'uppercase',
                }}
              >
                Physical Takeover Intercept
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  background: 'rgba(255, 59, 48, 0.25)',
                  border: '1px solid #FF3B30',
                  color: '#FF3B30',
                  padding: '1px 6px',
                  borderRadius: 4,
                }}
              >
                PAUSED (&lt;500ms SLA)
              </span>
            </div>
            <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 2 }}>
              Hardware input detected. Virtual automation halted until confirmed.
            </div>
          </div>
        </div>

        {onDismiss && (
          <button
            onClick={onDismiss}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94A3B8',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
              alignItems: 'center',
            }}
            title="Dismiss notification"
          >
            <DismissRegular style={{ fontSize: 18 }} />
          </button>
        )}
      </div>

      {/* Details Box */}
      <div
        style={{
          background: 'rgba(0, 0, 0, 0.4)',
          borderRadius: 6,
          padding: '10px 14px',
          border: '1px solid rgba(255, 136, 0, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
        }}
      >
        <div style={{ fontSize: 13, color: '#E2E8F0', fontWeight: 500 }}>
          {reason || 'Physical keyboard or mouse movement interrupted active automation sequence.'}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 11, color: '#94A3B8' }}>
          {app_name && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <DesktopRegular style={{ color: '#00FFCC' }} />
              Target: <strong style={{ color: '#F1F5F9' }}>{app_name}</strong>
            </span>
          )}
          {session_id && (
            <span>
              Session: <code style={{ color: '#FFB800' }}>{session_id}</code>
            </span>
          )}
          {timestamp && (
            <span>
              Time: <span style={{ color: '#CBD5E1' }}>{timestamp}</span>
            </span>
          )}
        </div>
      </div>

      {/* Decision Buttons */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
        <button
          onClick={() => onDecision('stop', session_id)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'rgba(255, 59, 48, 0.15)',
            border: '1px solid #FF3B30',
            color: '#FF3B30',
            borderRadius: 6,
            padding: '7px 16px',
            fontSize: 12,
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.15s ease-in-out',
            boxShadow: '0 0 10px rgba(255, 59, 48, 0.2)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(255, 59, 48, 0.3)';
            e.currentTarget.style.boxShadow = '0 0 15px rgba(255, 59, 48, 0.4)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(255, 59, 48, 0.15)';
            e.currentTarget.style.boxShadow = '0 0 10px rgba(255, 59, 48, 0.2)';
          }}
        >
          <StopRegular style={{ fontSize: 16 }} />
          ABORT AUTOMATION
        </button>

        <button
          onClick={() => onDecision('continue', session_id)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'rgba(0, 255, 204, 0.15)',
            border: '1px solid #00FFCC',
            color: '#00FFCC',
            borderRadius: 6,
            padding: '7px 18px',
            fontSize: 12,
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.15s ease-in-out',
            boxShadow: '0 0 12px rgba(0, 255, 204, 0.25)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(0, 255, 204, 0.3)';
            e.currentTarget.style.boxShadow = '0 0 18px rgba(0, 255, 204, 0.5)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(0, 255, 204, 0.15)';
            e.currentTarget.style.boxShadow = '0 0 12px rgba(0, 255, 204, 0.25)';
          }}
        >
          <PlayRegular style={{ fontSize: 16 }} />
          RESUME AUTOMATION
        </button>
      </div>
    </div>
  );
};
