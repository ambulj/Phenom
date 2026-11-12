import React, { useState } from 'react';
import {
  ArrowSyncRegular,
  WarningRegular,
  CheckmarkCircleRegular,
} from '@fluentui/react-icons';
import { GovernanceWatchdogStatePayload } from '../../types/protocol';

interface SubsystemGovernanceHUDProps {
  governanceState: GovernanceWatchdogStatePayload | null;
  onRemediate?: (subsystem: string, action: 'recycle_worker' | 'flush_stale_buffers' | 'trim_gpu_cache' | 'reset_circuit_breaker') => void;
  onResetBreaker?: (subsystem: string) => void;
}

export const SubsystemGovernanceHUD: React.FC<SubsystemGovernanceHUDProps> = ({
  governanceState,
  onRemediate,
  onResetBreaker,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);

  if (!governanceState) {
    return null;
  }

  const {
    is_active,
    subsystems,
    overall_health,
    active_anomalies,
    recent_remediations,
  } = governanceState;

  const stateColor = !is_active
    ? '#ef4444'
    : overall_health >= 0.90
    ? '#10b981'
    : overall_health >= 0.70
    ? '#f59e0b'
    : '#ef4444';

  return (
    <div
      style={{
        background: 'rgba(10, 16, 26, 0.94)',
        border: `1px solid ${stateColor}55`,
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(16px)',
        boxShadow: `0 4px 20px ${stateColor}22`,
        maxWidth: 460,
        margin: '8px 0',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #1e293b',
          paddingBottom: 6,
          marginBottom: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {overall_health >= 0.85 ? (
            <CheckmarkCircleRegular style={{ color: stateColor, fontSize: 16 }} />
          ) : (
            <WarningRegular style={{ color: stateColor, fontSize: 16 }} />
          )}
          <span style={{ fontWeight: 700, letterSpacing: 0.5, color: '#f8fafc' }}>
            SUBSYSTEM SELF-GOVERNANCE
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '1px 6px',
              borderRadius: 4,
              background: `${stateColor}22`,
              color: stateColor,
              border: `1px solid ${stateColor}44`,
              fontWeight: 600,
            }}
          >
            {(overall_health * 100).toFixed(0)}% HEALTH
          </span>
        </div>
        <button
          onClick={() => setIsMinimized(!isMinimized)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            fontSize: 11,
          }}
        >
          {isMinimized ? '[+]' : '[-]'}
        </button>
      </div>

      {!isMinimized && (
        <>
          {/* Active Anomalies Alert */}
          {active_anomalies.length > 0 && (
            <div
              style={{
                background: '#450a0a88',
                border: '1px solid #991b1b',
                borderRadius: 4,
                padding: '6px 8px',
                marginBottom: 8,
                fontSize: 10,
                color: '#fca5a5',
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 2 }}>Detected Anomalies:</div>
              {active_anomalies.map((ano, i) => (
                <div key={i}>• {ano}</div>
              ))}
            </div>
          )}

          {/* Subsystems Telemetry Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 6,
              marginBottom: 8,
            }}
          >
            {Object.values(subsystems).map((sub) => {
              const isNormal = sub.circuit_status === 'normal';
              const cardBorder = isNormal ? '#334155' : sub.circuit_status === 'degraded' ? '#f59e0b' : '#ef4444';

              return (
                <div
                  key={sub.subsystem_name}
                  style={{
                    background: '#0f172a88',
                    border: `1px solid ${cardBorder}66`,
                    borderRadius: 4,
                    padding: 6,
                    fontSize: 10,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                    <span style={{ color: '#f8fafc', fontWeight: 600 }}>{sub.subsystem_name}</span>
                    <span
                      style={{
                        fontSize: 9,
                        padding: '0 4px',
                        borderRadius: 3,
                        background: `${cardBorder}22`,
                        color: cardBorder,
                      }}
                    >
                      {sub.circuit_status.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ color: '#94a3b8', fontSize: 9 }}>
                    RAM: {sub.memory_mb.toFixed(0)}MB • VRAM: {sub.vram_mb.toFixed(0)}MB
                  </div>
                  {!isNormal && (
                    <div style={{ marginTop: 4, display: 'flex', gap: 4 }}>
                      <button
                        onClick={() => onResetBreaker?.(sub.subsystem_name)}
                        style={{
                          background: '#10b98122',
                          border: '1px solid #10b98155',
                          borderRadius: 3,
                          color: '#34d399',
                          cursor: 'pointer',
                          fontSize: 9,
                          padding: '1px 4px',
                        }}
                      >
                        Reset Breaker
                      </button>
                      <button
                        onClick={() => onRemediate?.(sub.subsystem_name, 'flush_stale_buffers')}
                        style={{
                          background: '#38bdf822',
                          border: '1px solid #38bdf855',
                          borderRadius: 3,
                          color: '#38bdf8',
                          cursor: 'pointer',
                          fontSize: 9,
                          padding: '1px 4px',
                        }}
                      >
                        Flush
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Quick Remediation Actions */}
          <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
            <button
              onClick={() => onRemediate?.('voice_action', 'flush_stale_buffers')}
              style={{
                flex: 1,
                background: '#1e293b',
                border: '1px solid #475569',
                borderRadius: 4,
                color: '#cbd5e1',
                padding: '4px',
                fontSize: 10,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
              }}
            >
              <ArrowSyncRegular style={{ fontSize: 10 }} /> Flush Queues
            </button>
            <button
              onClick={() => onRemediate?.('telepresence', 'trim_gpu_cache')}
              style={{
                flex: 1,
                background: '#1e293b',
                border: '1px solid #475569',
                borderRadius: 4,
                color: '#cbd5e1',
                padding: '4px',
                fontSize: 10,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
              }}
            >
              <ArrowSyncRegular style={{ fontSize: 10 }} /> Trim GPU VRAM
            </button>
          </div>

          {/* Recent Remediations Log */}
          <div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
              <span>Recent Remediations</span>
              <span>{recent_remediations.length} recorded</span>
            </div>
            <div
              style={{
                maxHeight: 90,
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: 3,
              }}
            >
              {recent_remediations.length === 0 ? (
                <div style={{ color: '#475569', fontSize: 10, fontStyle: 'italic' }}>
                  All subsystems operating nominal. No remediations required.
                </div>
              ) : (
                recent_remediations.slice(0, 4).map((rem) => (
                  <div
                    key={rem.remediation_id}
                    style={{
                      background: '#09101d',
                      border: '1px solid #1e293b',
                      borderRadius: 3,
                      padding: '3px 6px',
                      fontSize: 9,
                      display: 'flex',
                      justifyContent: 'space-between',
                      color: rem.success ? '#93c5fd' : '#fca5a5',
                    }}
                  >
                    <span>{rem.subsystem_name}: {rem.action_type}</span>
                    <span>{rem.success ? 'SUCCESS' : 'FAILED'}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
