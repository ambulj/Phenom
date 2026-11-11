import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  WarningRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
  ArrowSyncRegular,
  PulseRegular,
  ShieldDismissRegular,
} from '@fluentui/react-icons';

export interface WorkerHealthUI {
  agent_id: string;
  specialization: string;
  health_status: string; // HEALTHY, DEGRADED, BYZANTINE_FAULT, OFFLINE
  heartbeat_latency_ms: number;
  error_count: number;
  anomaly_score: number;
  last_seen: number;
}

export interface FailoverRecordUI {
  action_id: string;
  faulty_agent_id: string;
  reason: string;
  orphaned_task_ids: string[];
  timestamp: number;
}

interface SwarmWatchdogArbiterHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SwarmWatchdogArbiterHUD: React.FC<SwarmWatchdogArbiterHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [workers, setWorkers] = useState<WorkerHealthUI[]>([
    {
      agent_id: 'agent_codearchitect',
      specialization: 'CodeArchitect',
      health_status: 'HEALTHY',
      heartbeat_latency_ms: 14.2,
      error_count: 0,
      anomaly_score: 0.05,
      last_seen: Date.now() - 2000,
    },
    {
      agent_id: 'agent_securityauditor',
      specialization: 'SecurityAuditor',
      health_status: 'HEALTHY',
      heartbeat_latency_ms: 18.0,
      error_count: 0,
      anomaly_score: 0.08,
      last_seen: Date.now() - 1500,
    },
    {
      agent_id: 'agent_testorchestrator',
      specialization: 'TestOrchestrator',
      health_status: 'HEALTHY',
      heartbeat_latency_ms: 12.5,
      error_count: 0,
      anomaly_score: 0.02,
      last_seen: Date.now() - 1000,
    },
    {
      agent_id: 'agent_knowledgeresearcher',
      specialization: 'KnowledgeResearcher',
      health_status: 'HEALTHY',
      heartbeat_latency_ms: 22.1,
      error_count: 0,
      anomaly_score: 0.09,
      last_seen: Date.now() - 3000,
    },
  ]);

  const [failoverHistory, setFailoverHistory] = useState<FailoverRecordUI[]>([
    {
      action_id: 'failover_001',
      faulty_agent_id: 'agent_worker_legacy',
      reason: 'Heartbeat timeout > 5000ms',
      orphaned_task_ids: ['task_091'],
      timestamp: Date.now() - 7200000,
    },
  ]);

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'watchdog.update' && externalEvent.payload) {
      if (externalEvent.payload.workers) setWorkers(externalEvent.payload.workers);
      if (externalEvent.payload.history) setFailoverHistory(externalEvent.payload.history);
    }
  }, [externalEvent]);

  const handleQuarantine = (agentId: string) => {
    const updated = workers.map((w) => {
      if (w.agent_id === agentId) {
        return { ...w, health_status: 'BYZANTINE_FAULT', anomaly_score: 0.95 };
      }
      return w;
    });
    setWorkers(updated);

    const record: FailoverRecordUI = {
      action_id: `failover_${Date.now()}`,
      faulty_agent_id: agentId,
      reason: 'Manual quarantine trigger via Arbiter HUD',
      orphaned_task_ids: ['task_002'],
      timestamp: Date.now(),
    };
    setFailoverHistory([record, ...failoverHistory]);

    if (sendMessage) {
      sendMessage({
        type: 'arbiter.quarantine',
        payload: { agent_id: agentId, reason: record.reason },
      });
    }

    setFeedback(`Quarantined rogue agent ${agentId} and reclaimed tasks.`);
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleReassignOrphaned = () => {
    if (sendMessage) {
      sendMessage({
        type: 'arbiter.reassign',
        payload: {},
      });
    }
    setFeedback('Reassigned all orphaned tasks to healthy standby agents.');
    setTimeout(() => setFeedback(null), 3000);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 40,
        right: 40,
        width: 680,
        maxHeight: 'calc(100vh - 80px)',
        backgroundColor: 'rgba(10, 18, 28, 0.96)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 240, 255, 0.35)',
        borderRadius: 12,
        boxShadow: '0 8px 32px rgba(0, 240, 255, 0.15)',
        color: '#e2e8f0',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        fontFamily: 'Segoe UI, -apple-system, sans-serif',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(0, 240, 255, 0.05)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldDismissRegular style={{ color: '#00f0ff', fontSize: 20 }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, letterSpacing: 0.5 }}>
              BYZANTINE WORKER WATCHDOG & FAILOVER ARBITER
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 27-04 • Heartbeat Latency Radar • Guardian Isolation & Task Failover
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: 4,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <DismissRegular style={{ fontSize: 18 }} />
        </button>
      </div>

      {feedback && (
        <div
          style={{
            padding: '8px 18px',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            borderBottom: '1px solid rgba(16, 185, 129, 0.3)',
            color: '#34d399',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <CheckmarkCircleRegular style={{ fontSize: 16 }} />
          <span>{feedback}</span>
        </div>
      )}

      {/* Content scroll area */}
      <div style={{ padding: 18, overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Worker Health Heatmap */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#00f0ff', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <PulseRegular style={{ fontSize: 14 }} />
            WORKER NODE HEALTH TELEMETRY ({workers.length})
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
            {workers.map((w) => (
              <div
                key={w.agent_id}
                style={{
                  padding: '12px 14px',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  border:
                    w.health_status === 'BYZANTINE_FAULT'
                      ? '1px solid rgba(239, 68, 68, 0.5)'
                      : w.health_status === 'DEGRADED'
                      ? '1px solid rgba(245, 158, 11, 0.4)'
                      : '1px solid rgba(0, 240, 255, 0.2)',
                  borderRadius: 8,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>{w.specialization}</div>
                    <div style={{ fontSize: 10, color: '#64748b' }}>{w.agent_id}</div>
                  </div>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: 10,
                      backgroundColor:
                        w.health_status === 'BYZANTINE_FAULT'
                          ? 'rgba(239, 68, 68, 0.2)'
                          : w.health_status === 'DEGRADED'
                          ? 'rgba(245, 158, 11, 0.2)'
                          : 'rgba(16, 185, 129, 0.2)',
                      color:
                        w.health_status === 'BYZANTINE_FAULT'
                          ? '#f87171'
                          : w.health_status === 'DEGRADED'
                          ? '#fbbf24'
                          : '#34d399',
                      border:
                        w.health_status === 'BYZANTINE_FAULT'
                          ? '1px solid rgba(239, 68, 68, 0.4)'
                          : '1px solid rgba(16, 185, 129, 0.4)',
                    }}
                  >
                    {w.health_status}
                  </span>
                </div>

                {/* Heartbeat & Anomaly Score */}
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8' }}>
                  <span>Heartbeat: <strong style={{ color: '#00f0ff' }}>{w.heartbeat_latency_ms.toFixed(1)} ms</strong></span>
                  <span>Anomaly: <strong style={{ color: w.anomaly_score > 0.5 ? '#ef4444' : '#10b981' }}>{(w.anomaly_score * 100).toFixed(0)}%</strong></span>
                </div>

                {w.health_status !== 'BYZANTINE_FAULT' ? (
                  <button
                    onClick={() => handleQuarantine(w.agent_id)}
                    style={{
                      marginTop: 2,
                      padding: '4px 10px',
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: 4,
                      color: '#f87171',
                      fontSize: 10,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 4,
                    }}
                  >
                    <WarningRegular style={{ fontSize: 12 }} />
                    Quarantine Faulty Node
                  </button>
                ) : (
                  <div style={{ fontSize: 10, color: '#ef4444', textAlign: 'center', fontWeight: 600 }}>
                    NODE ISOLATED IN GUARDIAN JAIL
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Failover Actions & Rescue */}
        <div
          style={{
            padding: 12,
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid rgba(0, 240, 255, 0.15)',
            borderRadius: 8,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc' }}>Autonomous Failover & Rescue Engine</div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
              Re-auctions unassigned or orphaned task contracts with zero data loss (Rule 7).
            </div>
          </div>
          <button
            onClick={handleReassignOrphaned}
            style={{
              padding: '6px 14px',
              backgroundColor: '#00f0ff',
              border: 'none',
              borderRadius: 4,
              color: '#000',
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <ArrowSyncRegular style={{ fontSize: 13 }} />
            Reassign Orphaned Tasks
          </button>
        </div>

        {/* Failover Audit Log */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#f59e0b', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <WarningRegular style={{ fontSize: 14 }} />
            FAILOVER & QUARANTINE AUDIT TRAIL ({failoverHistory.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {failoverHistory.map((rec) => (
              <div
                key={rec.action_id}
                style={{
                  padding: '8px 12px',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: 6,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: 11, color: '#e2e8f0' }}>
                    <span style={{ color: '#ef4444', fontWeight: 600 }}>[QUARANTINE]</span> {rec.faulty_agent_id}: {rec.reason}
                  </div>
                  <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>
                    Reclaimed Tasks: {rec.orphaned_task_ids.join(', ') || 'None'}
                  </div>
                </div>
                <span style={{ fontSize: 10, color: '#94a3b8' }}>
                  {new Date(rec.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '10px 18px',
          borderTop: '1px solid rgba(0, 240, 255, 0.2)',
          fontSize: 11,
          color: '#64748b',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(0, 240, 255, 0.02)',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShieldCheckmarkRegular style={{ color: '#00f0ff' }} />
          Byzantine Anomaly Radar • Instant Guardian Isolation
        </span>
        <span>Failover Arbiter Active</span>
      </div>
    </div>
  );
};
