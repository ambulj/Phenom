import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  FlashRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
  WarningRegular,
  BugRegular,
  WrenchRegular,
  ArrowClockwiseRegular,
} from '@fluentui/react-icons';

export interface HealingRecordUI {
  record_id: string;
  target_tree_id: string;
  failing_node_id: string;
  taxonomy: string;
  root_cause: string;
  compensation_strategy: string;
  grafted_node_ids: string[];
  outcome_status: string; // GRAFTED_AND_RETRYING, RESOLVED, ABORTED
  timestamp: number;
}

interface SelfHealingOrchestratorHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SelfHealingOrchestratorHUD: React.FC<SelfHealingOrchestratorHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [simError, setSimError] = useState<string>('Permission denied: Unable to access restricted socket /var/run/node.sock');
  const [records, setRecords] = useState<HealingRecordUI[]>([
    {
      record_id: 'heal_init_01',
      target_tree_id: 'tree_init_001',
      failing_node_id: 'leaf_002',
      taxonomy: 'TIMEOUT_INTERRUPT',
      root_cause: 'Transient execution timeout during test benchmark (deadline exceeded > 25ms)',
      compensation_strategy: 'CHUNKED_RETRY_WITH_ADAPTIVE_SLA',
      grafted_node_ids: ['heal_88a1', 'heal_88a2'],
      outcome_status: 'RESOLVED',
      timestamp: Date.now() - 120000,
    },
    {
      record_id: 'heal_init_02',
      target_tree_id: 'tree_init_001',
      failing_node_id: 'leaf_003',
      taxonomy: 'PERMISSION_DENIED',
      root_cause: 'Access denied: Sandbox containment restricted file mutation to read-only',
      compensation_strategy: 'ELEVATE_OR_ISOLATE_IN_SANDBOX',
      grafted_node_ids: ['heal_99b1', 'heal_99b2'],
      outcome_status: 'GRAFTED_AND_RETRYING',
      timestamp: Date.now() - 45000,
    },
  ]);

  useEffect(() => {
    if (externalEvent?.type === 'HEALING_JOURNAL_UPDATED' && externalEvent.payload) {
      if (externalEvent.payload.records) setRecords(externalEvent.payload.records);
    }
  }, [externalEvent]);

  const handleSimulateHeal = () => {
    if (!simError.trim()) return;

    let tax = 'ENVIRONMENT_FAULT';
    let strat = 'FLUSH_TRANSIENT_BUFFERS_AND_RETRY';

    if (/permission|access denied/i.test(simError)) {
      tax = 'PERMISSION_DENIED';
      strat = 'ELEVATE_OR_ISOLATE_IN_SANDBOX';
    } else if (/not found|missing/i.test(simError)) {
      tax = 'RESOURCE_NOT_FOUND';
      strat = 'RECONSTRUCT_OR_PULL_DEPENDENCY';
    } else if (/timeout|deadline/i.test(simError)) {
      tax = 'TIMEOUT_INTERRUPT';
      strat = 'CHUNKED_RETRY_WITH_ADAPTIVE_SLA';
    } else if (/parse|json|schema/i.test(simError)) {
      tax = 'MALFORMED_OUTPUT';
      strat = 'SCHEMA_REPAIR_AND_SANITIZATION';
    }

    const newRecord: HealingRecordUI = {
      record_id: `heal_${Math.random().toString(16).substring(2, 8)}`,
      target_tree_id: 'tree_init_001',
      failing_node_id: `leaf_${Math.random().toString(16).substring(2, 6)}`,
      taxonomy: tax,
      root_cause: simError,
      compensation_strategy: strat,
      grafted_node_ids: [`heal_${Math.random().toString(16).substring(2, 6)}`, `heal_${Math.random().toString(16).substring(2, 6)}`],
      outcome_status: 'GRAFTED_AND_RETRYING',
      timestamp: Date.now(),
    };

    setRecords((prev) => [newRecord, ...prev]);

    sendMessage?.({
      type: 'CALL_TOOL',
      tool: 'intercept_and_heal_failure',
      args: {
        target_tree_id: 'tree_init_001',
        failing_node_id: 'leaf_002',
        raw_error: simError,
      },
    });
  };

  const handleResolveRecord = (recId: string) => {
    setRecords((prev) =>
      prev.map((r) => (r.record_id === recId ? { ...r, outcome_status: 'RESOLVED' } : r))
    );
  };

  const resolvedCount = records.filter((r) => r.outcome_status === 'RESOLVED').length;
  const resolutionRate = records.length > 0 ? Math.round((resolvedCount / records.length) * 100) : 100;

  return (
    <div
      style={{
        position: 'fixed',
        top: '60px',
        right: '20px',
        width: '740px',
        maxHeight: 'calc(100vh - 100px)',
        backgroundColor: 'rgba(11, 19, 32, 0.94)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(244, 63, 94, 0.35)',
        borderRadius: '12px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.65), 0 0 16px rgba(244, 63, 94, 0.2)',
        color: '#f8fafc',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid rgba(244, 63, 94, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(90deg, rgba(244, 63, 94, 0.12), transparent)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <WrenchRegular style={{ fontSize: '22px', color: '#f43f5e' }} />
          <div>
            <div style={{ fontSize: '15px', fontWeight: 600, letterSpacing: '0.5px', color: '#f43f5e' }}>
              SELF-HEALING DYNAMIC WORKFLOW ORCHESTRATOR
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              Resolution Rate: <span style={{ color: '#10b981', fontWeight: 600 }}>{resolutionRate}%</span> |{' '}
              {resolvedCount}/{records.length} Interceptions Healed
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <DismissRegular style={{ fontSize: '18px' }} />
        </button>
      </div>

      {/* Error Simulation & Interception Input */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '6px' }}>
          INTERCEPT & HEAL SIMULATED WORKFLOW EXCEPTION
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={simError}
            onChange={(e) => setSimError(e.target.value)}
            placeholder="e.g. Permission denied, timeout exceeded, or missing module"
            style={{
              flex: 1,
              backgroundColor: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              borderRadius: '6px',
              padding: '8px 12px',
              color: '#f1f5f9',
              fontSize: '12px',
              outline: 'none',
            }}
            onKeyDown={(e) => e.key === 'Enter' && handleSimulateHeal()}
          />
          <button
            onClick={handleSimulateHeal}
            style={{
              backgroundColor: '#e11d48',
              border: 'none',
              borderRadius: '6px',
              padding: '8px 16px',
              color: '#ffffff',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <ArrowClockwiseRegular style={{ fontSize: '14px' }} />
            Graft Repair
          </button>
        </div>
      </div>

      {/* Healing Journal Records */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        {records.map((rec) => {
          const isResolved = rec.outcome_status === 'RESOLVED';
          const taxColor =
            rec.taxonomy === 'PERMISSION_DENIED'
              ? '#f43f5e'
              : rec.taxonomy === 'TIMEOUT_INTERRUPT'
              ? '#f59e0b'
              : rec.taxonomy === 'RESOURCE_NOT_FOUND'
              ? '#38bdf8'
              : '#a855f7';

          return (
            <div
              key={rec.record_id}
              style={{
                backgroundColor: isResolved ? 'rgba(15, 23, 42, 0.5)' : 'rgba(30, 41, 59, 0.7)',
                border: `1px solid ${isResolved ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.4)'}`,
                borderRadius: '8px',
                padding: '12px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontFamily: 'monospace',
                      fontSize: '11px',
                      color: '#94a3b8',
                      backgroundColor: 'rgba(255, 255, 255, 0.06)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                    }}
                  >
                    {rec.record_id}
                  </span>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 600,
                      color: taxColor,
                      border: `1px solid ${taxColor}`,
                      borderRadius: '4px',
                      padding: '1px 6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <BugRegular style={{ fontSize: '11px' }} />
                    {rec.taxonomy}
                  </span>
                  <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                    Node: <span style={{ fontFamily: 'monospace', color: '#cbd5e1' }}>{rec.failing_node_id}</span>
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: isResolved ? '#10b981' : '#f59e0b',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    {isResolved ? (
                      <CheckmarkCircleRegular style={{ fontSize: '13px' }} />
                    ) : (
                      <WarningRegular style={{ fontSize: '13px' }} />
                    )}
                    {rec.outcome_status}
                  </span>

                  {!isResolved && (
                    <button
                      onClick={() => handleResolveRecord(rec.record_id)}
                      style={{
                        background: 'rgba(16, 185, 129, 0.15)',
                        border: '1px solid rgba(16, 185, 129, 0.4)',
                        borderRadius: '4px',
                        padding: '2px 8px',
                        color: '#34d399',
                        fontSize: '10px',
                        cursor: 'pointer',
                      }}
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>

              <div style={{ fontSize: '12px', color: '#fca5a5', fontFamily: 'monospace' }}>
                {rec.root_cause}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#cbd5e1' }}>
                <span style={{ color: '#38bdf8', fontWeight: 600 }}>Applied Strategy:</span>
                <span style={{ fontFamily: 'monospace' }}>{rec.compensation_strategy}</span>
              </div>

              {rec.grafted_node_ids && rec.grafted_node_ids.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#94a3b8' }}>
                  <span>Grafted Compensation Steps:</span>
                  {rec.grafted_node_ids.map((gid) => (
                    <span
                      key={gid}
                      style={{
                        fontFamily: 'monospace',
                        color: '#67e8f9',
                        backgroundColor: 'rgba(103, 232, 249, 0.1)',
                        padding: '1px 6px',
                        borderRadius: '3px',
                      }}
                    >
                      {gid}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '12px 20px',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.8)',
          fontSize: '11px',
          color: '#94a3b8',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ShieldCheckmarkRegular style={{ fontSize: '14px', color: '#10b981' }} />
          <span>Non-Destructive Plan Mutation (Rule 7)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FlashRegular style={{ fontSize: '14px', color: '#f43f5e' }} />
          <span>Autonomous In-Flight Repair</span>
        </div>
      </div>
    </div>
  );
};
