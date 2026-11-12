import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  ShieldCheckmarkRegular,
  CheckmarkCircleRegular,
  PulseRegular,
  WrenchRegular,
} from '@fluentui/react-icons';

export interface WatchdogIncidentUI {
  incident_id: string;
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  incident_type: string;
  process_name: string;
  details: string;
  timestamp: string;
  is_resolved: boolean;
}

export interface InterventionCardUI {
  card_id: string;
  incident_id: string;
  title: string;
  recommendation: string;
  action_type: 'GRACEFUL_RESTART' | 'APPLY_REPAIR_PATCH' | 'CLEAN_CACHE' | 'DISMISS_ALERT';
  target_process: string;
  confidence: number;
}

interface DesktopWatchdogHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const DesktopWatchdogHUD: React.FC<DesktopWatchdogHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [healthScore, setHealthScore] = useState<number>(0.85);
  const [healthStatus, setHealthStatus] = useState<'HEALTHY' | 'DEGRADED' | 'CRITICAL'>('DEGRADED');
  const [sensitivity] = useState<'CONSERVATIVE' | 'BALANCED' | 'AGGRESSIVE'>('BALANCED');

  const [incidents, setIncidents] = useState<WatchdogIncidentUI[]>([
    {
      incident_id: 'inc_b8a1',
      severity: 'WARNING',
      incident_type: 'BUILD_FAILURE',
      process_name: 'vite.exe',
      details: 'Compilation error in App.tsx line 42: missing closing bracket',
      timestamp: new Date().toLocaleTimeString(),
      is_resolved: false,
    },
    {
      incident_id: 'inc_c492',
      severity: 'INFO',
      incident_type: 'SYSTEM_ALERT',
      process_name: 'Notepad.exe',
      details: 'Pending unsaved scratchpad file buffer',
      timestamp: new Date().toLocaleTimeString(),
      is_resolved: false,
    },
  ]);

  const [cards, setCards] = useState<InterventionCardUI[]>([
    {
      card_id: 'card_01',
      incident_id: 'inc_b8a1',
      title: 'Build Failure Detected in vite.exe',
      recommendation: 'Run automated neuro-symbolic self-healing patch on failing source target.',
      action_type: 'APPLY_REPAIR_PATCH',
      target_process: 'vite.exe',
      confidence: 0.94,
    },
  ]);

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'watchdog.update' && externalEvent.payload) {
      if (externalEvent.payload.incidents) setIncidents(externalEvent.payload.incidents);
      if (externalEvent.payload.cards) setCards(externalEvent.payload.cards);
      if (externalEvent.payload.health) {
        setHealthScore(externalEvent.payload.health.health_score);
        setHealthStatus(externalEvent.payload.health.status);
      }
    }
  }, [externalEvent]);

  const handleExecuteRemediation = (cardId: string, processName: string, actionType: string) => {
    setCards((prev) => prev.filter((c) => c.card_id !== cardId));
    setIncidents((prev) =>
      prev.map((i) => (i.process_name === processName ? { ...i, is_resolved: true } : i))
    );

    const remaining = incidents.filter((i) => i.process_name !== processName && !i.is_resolved);
    if (remaining.length === 0) {
      setHealthStatus('HEALTHY');
      setHealthScore(1.0);
    }

    if (sendMessage) {
      sendMessage({
        type: 'watchdog.resolve_alert',
        payload: { card_id: cardId, action: 'EXECUTE' },
      });
    }

    setFeedback(`Remediation executed: ${actionType} on ${processName}`);
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleDismissCard = (cardId: string) => {
    setCards((prev) => prev.filter((c) => c.card_id !== cardId));

    if (sendMessage) {
      sendMessage({
        type: 'watchdog.resolve_alert',
        payload: { card_id: cardId, action: 'DISMISS' },
      });
    }

    setFeedback('Intervention card soft-dismissed. History preserved in watchdog.');
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleSimulateIncident = (severity: 'WARNING' | 'CRITICAL', type: string, proc: string, details: string) => {
    const newInc: WatchdogIncidentUI = {
      incident_id: `inc_${Math.random().toString(16).slice(2, 6)}`,
      severity,
      incident_type: type,
      process_name: proc,
      details,
      timestamp: new Date().toLocaleTimeString(),
      is_resolved: false,
    };

    setIncidents((prev) => [newInc, ...prev]);

    const newCard: InterventionCardUI = {
      card_id: `card_${Math.random().toString(16).slice(2, 6)}`,
      incident_id: newInc.incident_id,
      title: `${type.replace('_', ' ')} in ${proc}`,
      recommendation: severity === 'CRITICAL' ? `Gracefully restart ${proc} to prevent OS lockup.` : `Repair and reconcile ${proc} state.`,
      action_type: severity === 'CRITICAL' ? 'GRACEFUL_RESTART' : 'APPLY_REPAIR_PATCH',
      target_process: proc,
      confidence: 0.95,
    };

    setCards((prev) => [newCard, ...prev]);
    setHealthStatus(severity === 'CRITICAL' ? 'CRITICAL' : 'DEGRADED');
    setHealthScore(severity === 'CRITICAL' ? 0.35 : 0.7);

    setFeedback(`Simulated ${severity} incident in ${proc}`);
    setTimeout(() => setFeedback(null), 3000);
  };

  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return '#ff0055';
      case 'ERROR':
      case 'WARNING':
        return '#f59e0b';
      case 'INFO':
        return '#38bdf8';
      default:
        return '#00ffcc';
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        width: 520,
        backgroundColor: '#0a0d14',
        border: '1px solid #1f293d',
        borderRadius: 12,
        boxShadow: '0 8px 32px rgba(0,0,0,0.8), 0 0 16px rgba(0, 255, 204, 0.1)',
        color: '#e2e8f0',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        zIndex: 9999,
        overflow: 'hidden',
        backdropFilter: 'blur(16px)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          background: 'linear-gradient(90deg, rgba(0, 255, 204, 0.08) 0%, rgba(10, 13, 20, 0) 100%)',
          borderBottom: '1px solid #1f293d',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <PulseRegular style={{ color: '#00ffcc', fontSize: 18 }} />
          <span style={{ fontWeight: 600, fontSize: 13, letterSpacing: '0.05em', color: '#f8fafc' }}>
            DESKTOP WATCHDOG &amp; TASK INTERCEPTOR
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              backgroundColor: healthStatus === 'HEALTHY' ? 'rgba(0, 255, 204, 0.2)' : 'rgba(245, 158, 11, 0.2)',
              color: healthStatus === 'HEALTHY' ? '#00ffcc' : '#f59e0b',
              fontWeight: 600,
            }}
          >
            {healthStatus}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
            }}
          >
            <DismissRegular style={{ fontSize: 16 }} />
          </button>
        )}
      </div>

      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* System Health Gauge Bar */}
        <div
          style={{
            backgroundColor: '#070a0f',
            border: `1px solid ${getSeverityColor(healthStatus)}44`,
            borderRadius: 8,
            padding: 12,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase' }}>
              Host Stability Rating
            </span>
            <span style={{ fontSize: 14, fontWeight: 700, color: getSeverityColor(healthStatus) }}>
              {(healthScore * 100).toFixed(0)}%
            </span>
          </div>

          <div style={{ width: '100%', height: 4, backgroundColor: '#1e293b', borderRadius: 2 }}>
            <div
              style={{
                width: `${healthScore * 100}%`,
                height: '100%',
                backgroundColor: getSeverityColor(healthStatus),
                borderRadius: 2,
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#64748b' }}>
            <span>Policy: {sensitivity}</span>
            <span>{incidents.filter((i) => !i.is_resolved).length} Unresolved Incidents</span>
          </div>
        </div>

        {/* Proactive Intervention Card */}
        {cards.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Actionable Proactive Interventions</div>
            {cards.map((card) => (
              <div
                key={card.card_id}
                style={{
                  backgroundColor: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid #38bdf844',
                  borderRadius: 8,
                  padding: 12,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <WrenchRegular style={{ color: '#38bdf8', fontSize: 14 }} />
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>{card.title}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#00ffcc', fontWeight: 600 }}>
                    {(card.confidence * 100).toFixed(0)}% conf
                  </span>
                </div>

                <div style={{ fontSize: 11, color: '#cbd5e1' }}>{card.recommendation}</div>

                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <button
                    onClick={() => handleExecuteRemediation(card.card_id, card.target_process, card.action_type)}
                    style={{
                      flex: 1,
                      padding: '6px 12px',
                      borderRadius: 4,
                      backgroundColor: '#00ffcc',
                      color: '#0a0d14',
                      border: 'none',
                      fontSize: 11,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    Apply 1-Click Remediation
                  </button>
                  <button
                    onClick={() => handleDismissCard(card.card_id)}
                    style={{
                      padding: '6px 12px',
                      borderRadius: 4,
                      backgroundColor: '#0f172a',
                      border: '1px solid #334155',
                      color: '#94a3b8',
                      fontSize: 10,
                      cursor: 'pointer',
                    }}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div
            style={{
              padding: 12,
              borderRadius: 6,
              backgroundColor: '#070a0f',
              border: '1px solid #1e293b',
              textAlign: 'center',
              fontSize: 11,
              color: '#00ffcc',
            }}
          >
            All systems nominal. Zero active incident interventions pending.
          </div>
        )}

        {/* Recent Incident Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Active Incident Telemetry</div>
          <div style={{ maxHeight: 110, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
            {incidents.slice(0, 4).map((inc) => (
              <div
                key={inc.incident_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 8px',
                  backgroundColor: '#070a0f',
                  borderRadius: 4,
                  border: '1px solid #1e293b',
                  fontSize: 10,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span
                    style={{
                      padding: '1px 4px',
                      borderRadius: 3,
                      backgroundColor: `${getSeverityColor(inc.severity)}22`,
                      color: getSeverityColor(inc.severity),
                      fontWeight: 700,
                    }}
                  >
                    {inc.severity}
                  </span>
                  <span style={{ color: '#f1f5f9', fontWeight: 600 }}>{inc.process_name}:</span>
                  <span style={{ color: '#94a3b8' }}>{inc.details.slice(0, 32)}...</span>
                </div>
                <span style={{ color: inc.is_resolved ? '#00ffcc' : '#64748b' }}>
                  {inc.is_resolved ? 'RESOLVED' : inc.timestamp}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Simulation Triggers */}
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={() =>
              handleSimulateIncident('CRITICAL', 'HUNG_PROCESS', 'Code.exe', 'Editor worker hang timeout (14.5s)')
            }
            style={{
              flex: 1,
              padding: '5px 8px',
              borderRadius: 4,
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              color: '#ff0055',
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            Simulate Hung Process
          </button>
          <button
            onClick={() =>
              handleSimulateIncident('WARNING', 'BUILD_FAILURE', 'pytest.exe', 'Failed 1 test assertion in api')
            }
            style={{
              flex: 1,
              padding: '5px 8px',
              borderRadius: 4,
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              color: '#f59e0b',
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            Simulate Build Error
          </button>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div
            style={{
              padding: '6px 10px',
              backgroundColor: 'rgba(0, 255, 204, 0.1)',
              border: '1px solid #00ffcc44',
              borderRadius: 6,
              fontSize: 11,
              color: '#00ffcc',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <CheckmarkCircleRegular style={{ fontSize: 13 }} />
            <span>{feedback}</span>
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 9,
            color: '#475569',
            borderTop: '1px solid #1e293b',
            paddingTop: 8,
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <ShieldCheckmarkRegular style={{ color: '#00ffcc', fontSize: 11 }} />
            Proactive Non-Intrusive Watchdog Active
          </span>
          <span>Guardian SLA &lt; 25ms</span>
        </div>
      </div>
    </div>
  );
};
