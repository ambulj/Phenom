import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  AlertUrgentRegular,
  BrainCircuitRegular,
  CheckmarkRegular,
  SparkleRegular,
} from '@fluentui/react-icons';

export interface AmbientAlertHUDItem {
  alert_id: string;
  title: string;
  summary: string;
  category: string;
  urgency: number;
  source: string;
  action_suggestion?: string;
}

interface AmbientIntelligenceHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const AmbientIntelligenceHUD: React.FC<AmbientIntelligenceHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [focusMode, setFocusMode] = useState<string>('balanced');
  const [threshold, setThreshold] = useState<number>(0.4);
  const [suppressedCount, setSuppressedCount] = useState<number>(2);

  const [alerts, setAlerts] = useState<AmbientAlertHUDItem[]>([
    {
      alert_id: 'alt_01',
      title: 'Local GPU VRAM Optimal',
      summary: '8B Instruct model cached in NVIDIA VRAM (4.2 GB / 8.0 GB used). Zero cloud egress.',
      category: 'system',
      urgency: 0.25,
      source: 'gpu_monitor',
    },
    {
      alert_id: 'alt_02',
      title: 'Upcoming Architecture Sync',
      summary: 'Cross-vault Obsidian graph sync scheduled in 15 minutes.',
      category: 'calendar',
      urgency: 0.45,
      source: 'scheduler',
      action_suggestion: 'View Knowledge Canvas',
    },
    {
      alert_id: 'alt_03',
      title: 'Isolated Test Failure in Sandbox',
      summary: 'Diagnostic worker detected 1 regression in billing worktree test battery.',
      category: 'developer',
      urgency: 0.82,
      source: 'diagnostic_daemon',
      action_suggestion: 'Open Worktree Diff',
    },
  ]);

  const [briefing] = useState<string>(
    'Phenom Ambient Status: 3 active alerts. 1 critical issue in developer sandbox. All operations 100% offline local.'
  );

  useEffect(() => {
    if (externalEvent?.type === 'ambient.feed_update' && externalEvent.payload) {
      if (externalEvent.payload.focus_mode) setFocusMode(externalEvent.payload.focus_mode);
      if (externalEvent.payload.threshold !== undefined) setThreshold(externalEvent.payload.threshold);
      if (externalEvent.payload.delivered_alerts) setAlerts(externalEvent.payload.delivered_alerts);
      if (externalEvent.payload.suppressed_count !== undefined) setSuppressedCount(externalEvent.payload.suppressed_count);
    }
  }, [externalEvent]);

  const handleSetMode = (mode: string, th: number) => {
    setFocusMode(mode);
    setThreshold(th);
    if (sendMessage) {
      sendMessage({
        type: 'ambient.configure_filter',
        payload: { mode, custom_threshold: th },
      });
    }
  };

  const handleDismiss = (alertId: string) => {
    setAlerts((prev) => prev.filter((a) => a.alert_id !== alertId));
    if (sendMessage) {
      sendMessage({
        type: 'ambient.dismiss_alert',
        payload: { alert_id: alertId },
      });
    }
  };

  const getUrgencyColor = (u: number) => {
    if (u >= 0.75) return '#f87171'; // Critical red
    if (u >= 0.40) return '#facc15'; // Warning yellow
    return '#34d399'; // Informational emerald
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(10, 15, 26, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(245, 158, 11, 0.35)',
        borderRadius: 12,
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.7), 0 0 25px rgba(245, 158, 11, 0.18)',
        display: 'flex',
        flexDirection: 'column',
        color: '#e2e8f0',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          borderBottom: '1px solid rgba(245, 158, 11, 0.2)',
          background: 'rgba(180, 83, 9, 0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <AlertUrgentRegular style={{ fontSize: 22, color: '#f59e0b' }} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: 0.5, color: '#fbbf24' }}>
              PROACTIVE AMBIENT INTELLIGENCE & NOTIFICATION HUB
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 22-04 • Context-Aware Focus Filtering & Dynamic Alert Telemetry (AMB-02 / NOT-02)
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Mode Pill Group */}
          <div style={{ display: 'flex', background: 'rgba(255, 255, 255, 0.05)', borderRadius: 6, padding: 2 }}>
            {[
              { id: 'deep_focus', name: 'Deep Focus', th: 0.75 },
              { id: 'balanced', name: 'Balanced', th: 0.40 },
              { id: 'ambient', name: 'Ambient', th: 0.00 },
            ].map((m) => (
              <button
                key={m.id}
                onClick={() => handleSetMode(m.id, m.th)}
                style={{
                  background: focusMode === m.id ? 'rgba(245, 158, 11, 0.25)' : 'transparent',
                  color: focusMode === m.id ? '#fbbf24' : '#94a3b8',
                  border: 'none',
                  padding: '4px 10px',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: focusMode === m.id ? 600 : 400,
                }}
              >
                {m.name}
              </button>
            ))}
          </div>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: 4,
                display: 'flex',
              }}
            >
              <DismissRegular style={{ fontSize: 18 }} />
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Proactive Briefing Banner */}
        <div
          style={{
            padding: 14,
            borderRadius: 8,
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.25)',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <SparkleRegular style={{ fontSize: 24, color: '#f59e0b', flexShrink: 0 }} />
          <div style={{ flex: 1, fontSize: 13, color: '#fef3c7', lineHeight: 1.4 }}>
            {briefing}
          </div>
        </div>

        {/* Focus Mode & Filter Status Gauge */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 12,
          }}
        >
          <div
            style={{
              padding: 12,
              borderRadius: 8,
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <BrainCircuitRegular style={{ fontSize: 20, color: '#fbbf24' }} />
            <div>
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>Focus Gate Threshold</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc', marginTop: 2 }}>
                {(threshold * 100).toFixed(0)}% Urgency Minimum
              </div>
            </div>
          </div>

          <div
            style={{
              padding: 12,
              borderRadius: 8,
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: suppressedCount > 0 ? '#38bdf8' : '#94a3b8' }} />
            <div>
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>Suppressed Low-Priority Noise</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#38bdf8', marginTop: 2 }}>
                {suppressedCount} buffered alerts
              </div>
            </div>
          </div>
        </div>

        {/* Live Alerts Stream */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
            Active Delivered Alerts ({alerts.length})
          </div>

          {alerts.map((alert) => {
            const uColor = getUrgencyColor(alert.urgency);
            return (
              <div
                key={alert.alert_id}
                style={{
                  padding: 14,
                  borderRadius: 8,
                  background: 'rgba(255, 255, 255, 0.025)',
                  border: `1px solid ${alert.urgency >= 0.75 ? 'rgba(248, 113, 113, 0.4)' : 'rgba(255, 255, 255, 0.08)'}`,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        background: 'rgba(255, 255, 255, 0.08)',
                        color: '#94a3b8',
                        padding: '2px 6px',
                        borderRadius: 4,
                      }}
                    >
                      {alert.category}
                    </span>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>
                      {alert.title}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: uColor }}>
                      Urgency: {(alert.urgency * 100).toFixed(0)}%
                    </span>
                    <button
                      onClick={() => handleDismiss(alert.alert_id)}
                      style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: 'none',
                        color: '#94a3b8',
                        borderRadius: 4,
                        padding: '3px 8px',
                        fontSize: 11,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <CheckmarkRegular style={{ fontSize: 12 }} />
                      <span>Dismiss</span>
                    </button>
                  </div>
                </div>

                <div style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.4 }}>
                  {alert.summary}
                </div>

                {alert.action_suggestion && (
                  <div style={{ fontSize: 11, color: '#38bdf8', marginTop: 2 }}>
                    💡 Suggested Action: <strong>{alert.action_suggestion}</strong>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '8px 20px',
          background: 'rgba(0, 0, 0, 0.3)',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 11,
          color: '#64748b',
        }}
      >
        <div>Focus Mode: {focusMode.toUpperCase()} • Rule 4 100% Offline Local Daemon</div>
        <div>Guardian SLA &lt; 25.0ms • Non-Destructive Dismissal</div>
      </div>
    </div>
  );
};
