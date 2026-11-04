import React, { useState } from 'react';
import {
  ShieldTaskRegular,
  WrenchRegular,
  ErrorCircleRegular,
  CheckmarkCircleRegular,
  ArrowSyncRegular,
} from '@fluentui/react-icons';
import {
  KernelFabricStatePayload,
  KernelCrashEventPayload,
  SelfHealingPatchPayload,
} from '../../types/protocol';

interface KernelSelfHealingHUDProps {
  fabricState: KernelFabricStatePayload | null;
  onApplyPatch?: (patchId: string) => void;
  onScanVenv?: () => void;
}

export const KernelSelfHealingHUD: React.FC<KernelSelfHealingHUDProps> = ({
  fabricState,
  onApplyPatch,
  onScanVenv,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [expandedCrashId, setExpandedCrashId] = useState<string | null>(null);

  if (!fabricState) {
    return null;
  }

  const {
    is_monitoring,
    total_crashes_diagnosed,
    active_crashes,
    pending_patches,
    remediation_success_rate,
  } = fabricState;

  return (
    <div
      style={{
        background: 'rgba(8, 12, 28, 0.94)',
        border: '1px solid #ff336655',
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(14px)',
        boxShadow: '0 8px 32px rgba(255, 51, 102, 0.12)',
        maxWidth: 440,
        width: '100%',
        marginBottom: 12,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #1e293b',
          paddingBottom: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ShieldTaskRegular style={{ color: '#ff3366', fontSize: 16 }} />
          <span style={{ fontWeight: 600, color: '#f8fafc', letterSpacing: 0.5 }}>
            KERNEL FABRIC & SELF-HEALING
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              background: is_monitoring ? 'rgba(0, 255, 136, 0.15)' : 'rgba(255, 51, 102, 0.15)',
              color: is_monitoring ? '#00ff88' : '#ff3366',
              border: `1px solid ${is_monitoring ? '#00ff8855' : '#ff336655'}`,
            }}
          >
            {is_monitoring ? 'ETW ACTIVE' : 'HALTED'}
          </span>
        </div>
        <button
          onClick={() => setIsMinimized(!isMinimized)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#64748b',
            cursor: 'pointer',
            fontSize: 11,
          }}
        >
          {isMinimized ? '[EXPAND]' : '[MINIMIZE]'}
        </button>
      </div>

      {!isMinimized && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {/* Telemetry Metrics */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: 6,
              background: 'rgba(15, 23, 42, 0.7)',
              padding: '6px 8px',
              borderRadius: 6,
              border: '1px solid #1e293b',
              textAlign: 'center',
            }}
          >
            <div>
              <div style={{ color: '#94a3b8', fontSize: 9 }}>TOTAL CRASHES</div>
              <div style={{ color: '#f87171', fontWeight: 600, fontSize: 13 }}>
                {total_crashes_diagnosed}
              </div>
            </div>
            <div>
              <div style={{ color: '#94a3b8', fontSize: 9 }}>UNRESOLVED</div>
              <div style={{ color: '#ffb800', fontWeight: 600, fontSize: 13 }}>
                {active_crashes.length}
              </div>
            </div>
            <div>
              <div style={{ color: '#94a3b8', fontSize: 9 }}>HEAL SUCCESS</div>
              <div style={{ color: '#00ff88', fontWeight: 600, fontSize: 13 }}>
                {(remediation_success_rate * 100).toFixed(0)}%
              </div>
            </div>
          </div>

          {/* Pending Remediation Patches (Tier 1 Preview Gate) */}
          {pending_patches.length > 0 && (
            <div>
              <div style={{ color: '#00f0ff', fontSize: 11, marginBottom: 4, fontWeight: 600 }}>
                PENDING REMEDIATION PATCHES ({pending_patches.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {pending_patches.map((patch: SelfHealingPatchPayload) => (
                  <div
                    key={patch.patch_id}
                    style={{
                      background: 'rgba(0, 240, 255, 0.08)',
                      border: '1px solid #00f0ff44',
                      borderRadius: 6,
                      padding: '8px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <WrenchRegular style={{ color: '#00f0ff', fontSize: 14 }} />
                        <span style={{ color: '#f1f5f9', fontWeight: 600, fontSize: 11 }}>
                          {patch.action_type}
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: 9,
                          padding: '1px 5px',
                          borderRadius: 3,
                          background: 'rgba(255, 184, 0, 0.2)',
                          color: '#ffb800',
                        }}
                      >
                        TIER 1 CONFIRMATION
                      </span>
                    </div>

                    <div style={{ color: '#94a3b8', fontSize: 10 }}>
                      Target: <span style={{ color: '#e2e8f0' }}>{patch.target_entity}</span>
                    </div>
                    <div
                      style={{
                        background: 'rgba(15, 23, 42, 0.9)',
                        padding: '4px 6px',
                        borderRadius: 4,
                        fontSize: 9,
                        color: '#38bdf8',
                        overflowX: 'auto',
                      }}
                    >
                      $ {patch.proposed_command}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
                      <button
                        onClick={() => onApplyPatch && onApplyPatch(patch.patch_id)}
                        style={{
                          background: 'rgba(0, 255, 136, 0.2)',
                          border: '1px solid #00ff8866',
                          color: '#00ff88',
                          borderRadius: 4,
                          padding: '3px 8px',
                          fontSize: 10,
                          cursor: 'pointer',
                          fontWeight: 600,
                        }}
                      >
                        CONFIRM & APPLY PATCH
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Active Crash Log */}
          <div>
            <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 4 }}>
              RECENT CRASHES ({active_crashes.length})
            </div>
            {active_crashes.length === 0 ? (
              <div
                style={{
                  padding: '10px',
                  textAlign: 'center',
                  color: '#64748b',
                  fontSize: 11,
                  border: '1px dashed #334155',
                  borderRadius: 6,
                }}
              >
                No active kernel crashes detected. System nominal.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 160, overflowY: 'auto' }}>
                {active_crashes.map((crash: KernelCrashEventPayload) => {
                  const isExpanded = expandedCrashId === crash.event_id;
                  return (
                    <div
                      key={crash.event_id}
                      style={{
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid #334155',
                        borderRadius: 6,
                        padding: '6px 8px',
                      }}
                    >
                      <div
                        onClick={() => setExpandedCrashId(isExpanded ? null : crash.event_id)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          cursor: 'pointer',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          {crash.is_resolved ? (
                            <CheckmarkCircleRegular style={{ color: '#00ff88', fontSize: 14 }} />
                          ) : (
                            <ErrorCircleRegular style={{ color: '#ff3366', fontSize: 14 }} />
                          )}
                          <span style={{ color: '#f1f5f9', fontWeight: 500 }}>
                            {crash.process_name}
                          </span>
                          <span style={{ color: '#94a3b8', fontSize: 10 }}>
                            [{crash.exception_code}]
                          </span>
                        </div>
                        <span style={{ color: '#64748b', fontSize: 10 }}>
                          {isExpanded ? '[-] LESS' : '[+] MORE'}
                        </span>
                      </div>

                      <div style={{ color: '#fbbf24', fontSize: 10, marginTop: 4 }}>
                        Diagnosis: {crash.root_cause_diagnosis}
                      </div>

                      {isExpanded && (
                        <div
                          style={{
                            marginTop: 6,
                            background: 'rgba(2, 6, 23, 0.9)',
                            padding: '6px',
                            borderRadius: 4,
                            fontSize: 9,
                            color: '#94a3b8',
                            maxHeight: 100,
                            overflowY: 'auto',
                          }}
                        >
                          <div>STACK TRACE (Rule 11 Scrubbed):</div>
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{crash.stack_trace}</pre>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div style={{ borderTop: '1px solid #1e293b', paddingTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
            <button
              onClick={() => onScanVenv && onScanVenv()}
              style={{
                background: 'rgba(56, 189, 248, 0.15)',
                border: '1px solid #38bdf855',
                color: '#38bdf8',
                borderRadius: 4,
                padding: '4px 8px',
                fontSize: 10,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <ArrowSyncRegular style={{ fontSize: 12 }} />
              SCAN VIRTUAL ENVIRONMENT
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
