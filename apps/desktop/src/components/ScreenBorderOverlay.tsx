import React, { useEffect, useState } from 'react';
import { Button, ProgressBar } from '@fluentui/react-components';
import { PlayRegular, DismissRegular, WarningRegular } from '@fluentui/react-icons';

export interface ScreenOverlayState {
  state: 'idle' | 'active' | 'success' | 'error' | 'takeover';
  color?: string;
  message?: string;
  timeoutSeconds?: number;
}

export interface ClickTarget {
  x: number;
  y: number;
  durationMs?: number;
}

export interface TickerItem {
  timestamp: string;
  text: string;
  step?: number;
  totalSteps?: number;
}

interface ScreenBorderOverlayProps {
  overlayState: ScreenOverlayState;
  clickTarget: ClickTarget | null;
  tickerItems: TickerItem[];
  onResumeAutomation?: () => void;
  onStopAutomation?: () => void;
}

export const ScreenBorderOverlay: React.FC<ScreenBorderOverlayProps> = ({
  overlayState,
  clickTarget,
  tickerItems,
  onResumeAutomation,
  onStopAutomation
}) => {
  const [countdown, setCountdown] = useState<number>(10);

  useEffect(() => {
    if (overlayState.state === 'takeover') {
      const initialSeconds = overlayState.timeoutSeconds || 10;
      setCountdown(initialSeconds);
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            if (onStopAutomation) {
              onStopAutomation();
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [overlayState.state, overlayState.timeoutSeconds, onStopAutomation]);

  if (overlayState.state === 'idle' && !clickTarget && tickerItems.length === 0) {
    return null;
  }

  const getBorderColor = (): string => {
    switch (overlayState.state) {
      case 'active':
        return '#0052FF'; // Electric Cobalt
      case 'success':
        return '#CCFF00'; // Acid Lime
      case 'error':
        return '#EF4444'; // Stark Crimson
      case 'takeover':
        return '#F97316'; // Warning Orange
      default:
        return 'transparent';
    }
  };

  const borderColor = getBorderColor();
  const showBorder = overlayState.state !== 'idle';

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 999999,
        pointerEvents: overlayState.state === 'takeover' ? 'auto' : 'none',
        boxSizing: 'border-box',
        border: showBorder ? `4px solid ${borderColor}` : 'none',
        boxShadow: showBorder ? `inset 0 0 24px ${borderColor}66, 0 0 16px ${borderColor}44` : 'none',
        transition: 'border 0.25s ease, box-shadow 0.25s ease',
        overflow: 'hidden'
      }}
    >
      <style>{`
        @keyframes pulseClickRing {
          0% { transform: translate(-50%, -50%) scale(0.4); opacity: 1; }
          100% { transform: translate(-50%, -50%) scale(1.8); opacity: 0; }
        }
        @keyframes flashBorder {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>

      {/* Click Target Concentric Ring Animation (Cobalt & Acid Lime) */}
      {clickTarget && (
        <div
          style={{
            position: 'absolute',
            left: clickTarget.x,
            top: clickTarget.y,
            pointerEvents: 'none'
          }}
        >
          {/* Outer Pulsing Concentric Ring */}
          <div
            style={{
              position: 'absolute',
              width: 56,
              height: 56,
              borderRadius: '50%',
              border: '2px solid #0052FF',
              boxShadow: '0 0 12px #0052FF',
              animation: 'pulseClickRing 0.3s ease-out forwards'
            }}
          />
          {/* Inner Target Center Dot */}
          <div
            style={{
              position: 'absolute',
              width: 14,
              height: 14,
              borderRadius: '50%',
              background: '#CCFF00',
              transform: 'translate(-50%, -50%)',
              boxShadow: '0 0 10px #CCFF00'
            }}
          />
        </div>
      )}

      {/* Live Action Ticker Feed (Top-Right) */}
      {tickerItems.length > 0 && (
        <div
          style={{
            position: 'absolute',
            top: 20,
            right: 20,
            background: 'rgba(8, 11, 16, 0.92)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(0, 82, 255, 0.35)',
            borderRadius: 10,
            padding: '8px 14px',
            color: '#f8fafc',
            fontFamily: 'Consolas, monospace',
            fontSize: '12px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.7), 0 0 12px rgba(0, 82, 255, 0.25)',
            maxWidth: 420
          }}
        >
          <div style={{ fontWeight: 600, color: '#CCFF00', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#CCFF00', boxShadow: '0 0 6px #CCFF00', display: 'inline-block' }} />
            Screen Action Ticker
          </div>
          {tickerItems.slice(-3).map((item, idx) => (
            <div key={idx} style={{ opacity: idx === tickerItems.slice(-3).length - 1 ? 1 : 0.65, marginTop: 2 }}>
              <span style={{ color: '#0052FF', fontWeight: 600 }}>[{item.timestamp}]</span> {item.text}
            </div>
          ))}
        </div>
      )}

      {/* Human Takeover Interruption Modal */}
      {overlayState.state === 'takeover' && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            background: '#080B10',
            border: '2px solid #0052FF',
            borderRadius: 16,
            padding: '24px 32px',
            color: '#f8fafc',
            boxShadow: '0 20px 60px rgba(0,0,0,0.85), 0 0 30px rgba(0, 82, 255, 0.35)',
            textAlign: 'center',
            maxWidth: 460,
            width: '90%'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
            <div style={{ background: 'rgba(249, 115, 22, 0.15)', borderRadius: '50%', padding: 12, border: '1px solid rgba(249, 115, 22, 0.3)' }}>
              <WarningRegular style={{ fontSize: 36, color: '#F97316' }} />
            </div>
          </div>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>
            User Interaction Detected
          </h3>
          <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: '#94a3b8', lineHeight: 1.5 }}>
            Physical mouse or keyboard activity was detected while automation was controlling the screen. Automation is safely paused.
          </p>
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#cbd5e1', marginBottom: 6 }}>
              <span>Auto-abort in:</span>
              <span style={{ fontWeight: 600, color: '#F97316' }}>{countdown}s</span>
            </div>
            <ProgressBar value={countdown / 10} color="warning" />
          </div>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <Button
              appearance="primary"
              icon={<PlayRegular />}
              onClick={onResumeAutomation}
              style={{ background: 'linear-gradient(135deg, #0052FF, #1a66ff)', borderColor: '#0052FF', color: '#ffffff', fontWeight: 600 }}
            >
              Resume Automation
            </Button>
            <Button
              appearance="secondary"
              icon={<DismissRegular />}
              onClick={onStopAutomation}
              style={{ background: '#EF4444', borderColor: '#EF4444', color: '#ffffff' }}
            >
              Stop & Abort
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
