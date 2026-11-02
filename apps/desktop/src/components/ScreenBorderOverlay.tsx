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

export interface HudAnnotationItem {
  id: string;
  name: string;
  control_type?: string;
  bbox: [number, number, number, number]; // [x, y, width, height]
  confidence?: number;
  color?: string; // hex color, default #0052FF
}

interface ScreenBorderOverlayProps {
  overlayState: ScreenOverlayState;
  clickTarget: ClickTarget | null;
  tickerItems: TickerItem[];
  annotations?: HudAnnotationItem[];
  onResumeAutomation?: () => void;
  onStopAutomation?: () => void;
}

export const ScreenBorderOverlay: React.FC<ScreenBorderOverlayProps> = ({
  overlayState,
  clickTarget,
  tickerItems,
  annotations = [],
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

  if (overlayState.state === 'idle' && !clickTarget && tickerItems.length === 0 && (!annotations || annotations.length === 0)) {
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

      {/* Live Cyber HUD Bounding Box Annotations (Electric Cobalt & Acid Lime) */}
      {annotations && annotations.map((anno) => {
        const [x, y, w, h] = anno.bbox;
        const accentColor = anno.color || '#0052FF';
        return (
          <div
            key={anno.id}
            data-testid={`hud-annotation-${anno.id}`}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: Math.max(w, 24),
              height: Math.max(h, 24),
              boxSizing: 'border-box',
              border: `2px solid ${accentColor}`,
              boxShadow: `0 0 14px ${accentColor}88, inset 0 0 8px ${accentColor}44`,
              borderRadius: 4,
              pointerEvents: 'none',
              transition: 'all 0.2s ease-out'
            }}
          >
            {/* Cyber Corner Bracket Accents (Acid Lime) */}
            <div style={{ position: 'absolute', top: -3, left: -3, width: 8, height: 8, borderTop: '3px solid #CCFF00', borderLeft: '3px solid #CCFF00' }} />
            <div style={{ position: 'absolute', top: -3, right: -3, width: 8, height: 8, borderTop: '3px solid #CCFF00', borderRight: '3px solid #CCFF00' }} />
            <div style={{ position: 'absolute', bottom: -3, left: -3, width: 8, height: 8, borderBottom: '3px solid #CCFF00', borderLeft: '3px solid #CCFF00' }} />
            <div style={{ position: 'absolute', bottom: -3, right: -3, width: 8, height: 8, borderBottom: '3px solid #CCFF00', borderRight: '3px solid #CCFF00' }} />

            {/* Floating Tag Badge */}
            <div
              style={{
                position: 'absolute',
                bottom: '100%',
                left: 0,
                marginBottom: 4,
                background: 'rgba(8, 11, 16, 0.94)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(0, 82, 255, 0.45)',
                borderRadius: 4,
                padding: '2px 7px',
                color: '#CCFF00',
                fontFamily: 'Consolas, monospace',
                fontSize: '10px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                whiteSpace: 'nowrap',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.8)'
              }}
            >
              <span style={{ color: '#0052FF', marginRight: 4 }}>
                {anno.control_type ? `[${anno.control_type}]` : '[TARGET]'}
              </span>
              {anno.name}
            </div>
          </div>
        );
      })}

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
          <h2 style={{ margin: '0 0 8px 0', fontSize: '20px', fontWeight: 600, color: '#f8fafc' }}>Automation Paused</h2>
          <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: '#94a3b8', lineHeight: 1.5 }}>
            {overlayState.message || 'User interaction detected. Automation has been paused for safety.'}
          </p>
          <div style={{ margin: '16px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b', marginBottom: 4 }}>
              <span>Auto-stop in</span>
              <span>{countdown}s</span>
            </div>
            <ProgressBar value={countdown / (overlayState.timeoutSeconds || 10)} color="warning" />
          </div>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 20 }}>
            <Button
              appearance="primary"
              icon={<PlayRegular />}
              onClick={onResumeAutomation}
              style={{ background: '#CCFF00', color: '#080B10', fontWeight: 600, border: 'none' }}
            >
              Continue Task
            </Button>
            <Button
              appearance="secondary"
              icon={<DismissRegular />}
              onClick={onStopAutomation}
              style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#EF4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}
            >
              Stop & Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
