import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  BranchForkRegular,
  FlashRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
  TimerRegular,
  FilterRegular,
  WarningRegular,
} from '@fluentui/react-icons';

export interface BranchStepUI {
  step_id: string;
  title: string;
  action_type: string;
  estimated_latency_ms: number;
  risk_factor: number;
}

export interface PlanBranchUI {
  branch_id: string;
  name: string;
  branch_type: string; // NOMINAL_PRIMARY, CONTINGENCY_EXPEDIENT, DEFENSIVE_CONSERVATIVE
  description: string;
  steps: BranchStepUI[];
  feasibility_score: number;
  risk_score: number;
  estimated_total_latency_ms: number;
  is_selected: boolean;
  is_pruned: boolean;
}

interface AdaptiveBranchPlannerHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const AdaptiveBranchPlannerHUD: React.FC<AdaptiveBranchPlannerHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [targetId, setTargetId] = useState<string>('Autonomous System Health & Safety Verification');
  const [maxRisk, setMaxRisk] = useState<number>(0.30);
  const [branches, setBranches] = useState<PlanBranchUI[]>([
    {
      branch_id: 'branch_nom_01',
      name: 'Nominal Direct Path',
      branch_type: 'NOMINAL_PRIMARY',
      description: 'Standard sequential execution with full contextual inspection and invariant assertions.',
      feasibility_score: 0.92,
      risk_score: 0.15,
      estimated_total_latency_ms: 125.0,
      is_selected: true,
      is_pruned: false,
      steps: [
        { step_id: 's1', title: 'Inspect AST & Runtime State', action_type: 'INSPECT', estimated_latency_ms: 25.0, risk_factor: 0.05 },
        { step_id: 's2', title: 'Execute Primary State Mutation', action_type: 'EXECUTE', estimated_latency_ms: 70.0, risk_factor: 0.20 },
        { step_id: 's3', title: 'Verify System Invariants & SLA', action_type: 'VERIFY', estimated_latency_ms: 30.0, risk_factor: 0.05 },
      ],
    },
    {
      branch_id: 'branch_exp_02',
      name: 'Contingency Expedient Path',
      branch_type: 'CONTINGENCY_EXPEDIENT',
      description: 'Fast path skipping non-essential telemetry to maximize throughput under tight deadlines.',
      feasibility_score: 0.78,
      risk_score: 0.38,
      estimated_total_latency_ms: 65.0,
      is_selected: false,
      is_pruned: false,
      steps: [
        { step_id: 's4', title: 'Fast-Track Dependency Check', action_type: 'INSPECT', estimated_latency_ms: 10.0, risk_factor: 0.15 },
        { step_id: 's5', title: 'Parallel Action Dispatch', action_type: 'EXECUTE', estimated_latency_ms: 40.0, risk_factor: 0.35 },
        { step_id: 's6', title: 'Lightweight Heartbeat Assertion', action_type: 'VERIFY', estimated_latency_ms: 15.0, risk_factor: 0.10 },
      ],
    },
    {
      branch_id: 'branch_def_03',
      name: 'Defensive Isolated Fallback',
      branch_type: 'DEFENSIVE_CONSERVATIVE',
      description: 'Maximum safety execution wrapped in complete memory snapshotting and AST jail isolation.',
      feasibility_score: 0.88,
      risk_score: 0.06,
      estimated_total_latency_ms: 245.0,
      is_selected: false,
      is_pruned: false,
      steps: [
        { step_id: 's7', title: 'Capture Pre-Execution Memory Snapshot', action_type: 'ROLLBACK_GUARD', estimated_latency_ms: 40.0, risk_factor: 0.02 },
        { step_id: 's8', title: 'Deep AST Security & Constraint Analysis', action_type: 'INSPECT', estimated_latency_ms: 50.0, risk_factor: 0.02 },
        { step_id: 's9', title: 'Guarded Stepwise Action Dispatch', action_type: 'EXECUTE', estimated_latency_ms: 110.0, risk_factor: 0.08 },
        { step_id: 's10', title: 'Strict 100-Cycle Guardian SLA Verification', action_type: 'VERIFY', estimated_latency_ms: 45.0, risk_factor: 0.01 },
      ],
    },
  ]);

  useEffect(() => {
    if (externalEvent?.type === 'SPECULATIVE_BRANCHES_UPDATED' && externalEvent.payload) {
      if (externalEvent.payload.target_id) setTargetId(externalEvent.payload.target_id);
      if (externalEvent.payload.branches) setBranches(externalEvent.payload.branches);
    }
  }, [externalEvent]);

  const handleSelectBranch = (branchId: string) => {
    setBranches((prev) =>
      prev.map((b) => ({
        ...b,
        is_selected: b.branch_id === branchId,
      }))
    );
  };

  const handlePruneBranches = () => {
    setBranches((prev) => {
      let viableCount = 0;
      const updated = prev.map((b) => {
        const shouldPrune = b.risk_score > maxRisk || b.feasibility_score < 0.70;
        if (!shouldPrune) viableCount++;
        return {
          ...b,
          is_pruned: shouldPrune,
          is_selected: shouldPrune ? false : b.is_selected,
        };
      });

      // Ensure one viable branch is selected
      if (viableCount > 0 && !updated.some((b) => b.is_selected && !b.is_pruned)) {
        const firstViable = updated.find((b) => !b.is_pruned);
        if (firstViable) firstViable.is_selected = true;
      }
      return updated;
    });

    sendMessage?.({
      type: 'CALL_TOOL',
      tool: 'prune_nonviable_branches',
      args: { target_id: targetId, max_acceptable_risk: maxRisk, min_acceptable_feasibility: 0.70 },
    });
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: '60px',
        right: '20px',
        width: '720px',
        maxHeight: 'calc(100vh - 100px)',
        backgroundColor: 'rgba(11, 19, 32, 0.94)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(56, 189, 248, 0.35)',
        borderRadius: '12px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.65), 0 0 16px rgba(56, 189, 248, 0.2)',
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
          borderBottom: '1px solid rgba(56, 189, 248, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(90deg, rgba(56, 189, 248, 0.12), transparent)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <BranchForkRegular style={{ fontSize: '22px', color: '#38bdf8' }} />
          <div>
            <div style={{ fontSize: '15px', fontWeight: 600, letterSpacing: '0.5px', color: '#38bdf8' }}>
              ADAPTIVE SPECULATIVE BRANCH PLANNER
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              Objective: <span style={{ color: '#e2e8f0' }}>{targetId}</span>
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

      {/* Pruning Thresholds Bar */}
      <div
        style={{
          padding: '12px 20px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'rgba(15, 23, 42, 0.6)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px', color: '#cbd5e1' }}>
          <span>Risk Tolerance:</span>
          <input
            type="range"
            min="0.10"
            max="0.50"
            step="0.05"
            value={maxRisk}
            onChange={(e) => setMaxRisk(parseFloat(e.target.value))}
            style={{ width: '120px', accentColor: '#38bdf8' }}
          />
          <span style={{ fontFamily: 'monospace', color: maxRisk > 0.30 ? '#f59e0b' : '#38bdf8' }}>
            {Math.round(maxRisk * 100)}%
          </span>
        </div>

        <button
          onClick={handlePruneBranches}
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.2)',
            border: '1px solid rgba(239, 68, 68, 0.5)',
            borderRadius: '6px',
            padding: '6px 14px',
            color: '#fca5a5',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <FilterRegular style={{ fontSize: '13px' }} />
          Prune Non-Viable Branches
        </button>
      </div>

      {/* Branch Cards */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
      >
        {branches.map((b) => {
          const isNominal = b.branch_type === 'NOMINAL_PRIMARY';
          const isExpedient = b.branch_type === 'CONTINGENCY_EXPEDIENT';

          const typeColor = isNominal ? '#38bdf8' : isExpedient ? '#f59e0b' : '#10b981';

          return (
            <div
              key={b.branch_id}
              style={{
                backgroundColor: b.is_pruned
                  ? 'rgba(15, 23, 42, 0.3)'
                  : b.is_selected
                  ? 'rgba(30, 41, 59, 0.8)'
                  : 'rgba(15, 23, 42, 0.6)',
                border: `1px solid ${
                  b.is_pruned
                    ? 'rgba(239, 68, 68, 0.25)'
                    : b.is_selected
                    ? 'rgba(56, 189, 248, 0.6)'
                    : 'rgba(255, 255, 255, 0.08)'
                }`,
                borderRadius: '8px',
                padding: '14px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                opacity: b.is_pruned ? 0.6 : 1.0,
                position: 'relative',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 600,
                      color: typeColor,
                      border: `1px solid ${typeColor}`,
                      borderRadius: '4px',
                      padding: '2px 6px',
                    }}
                  >
                    {b.branch_type}
                  </span>
                  <span style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc' }}>
                    {b.name}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {b.is_pruned ? (
                    <span
                      style={{
                        fontSize: '11px',
                        color: '#f87171',
                        backgroundColor: 'rgba(239, 68, 68, 0.15)',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <WarningRegular style={{ fontSize: '12px' }} />
                      PRUNED
                    </span>
                  ) : b.is_selected ? (
                    <span
                      style={{
                        fontSize: '11px',
                        color: '#38bdf8',
                        backgroundColor: 'rgba(56, 189, 248, 0.15)',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <CheckmarkCircleRegular style={{ fontSize: '13px' }} />
                      ACTIVE PATH
                    </span>
                  ) : (
                    <button
                      onClick={() => handleSelectBranch(b.branch_id)}
                      style={{
                        background: 'rgba(56, 189, 248, 0.15)',
                        border: '1px solid rgba(56, 189, 248, 0.3)',
                        borderRadius: '4px',
                        padding: '3px 10px',
                        color: '#38bdf8',
                        fontSize: '11px',
                        cursor: 'pointer',
                      }}
                    >
                      Select Path
                    </button>
                  )}
                </div>
              </div>

              <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                {b.description}
              </div>

              {/* Metrics Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '8px',
                  backgroundColor: 'rgba(15, 23, 42, 0.5)',
                  padding: '8px 12px',
                  borderRadius: '6px',
                }}
              >
                <div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>FEASIBILITY</div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#10b981' }}>
                    {Math.round(b.feasibility_score * 100)}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>RISK FACTOR</div>
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: b.risk_score > 0.25 ? '#f43f5e' : '#38bdf8',
                    }}
                  >
                    {Math.round(b.risk_score * 100)}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>EST. LATENCY</div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <TimerRegular style={{ fontSize: '12px', color: '#94a3b8' }} />
                    {b.estimated_total_latency_ms}ms
                  </div>
                </div>
              </div>

              {/* Steps Sequence */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>STEP SEQUENCE:</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {b.steps.map((st, idx) => (
                    <div
                      key={st.step_id}
                      style={{
                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '4px',
                        padding: '3px 8px',
                        fontSize: '11px',
                        color: '#cbd5e1',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      <span style={{ color: '#38bdf8', fontWeight: 600 }}>{idx + 1}.</span>
                      <span>{st.title}</span>
                      <span
                        style={{
                          fontSize: '9px',
                          color: st.risk_factor > 0.2 ? '#f87171' : '#34d399',
                          backgroundColor: 'rgba(0, 0, 0, 0.3)',
                          padding: '1px 4px',
                          borderRadius: '2px',
                        }}
                      >
                        {st.action_type}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
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
          <span>Non-Destructive Pruning History (Rule 7)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FlashRegular style={{ fontSize: '14px', color: '#38bdf8' }} />
          <span>Local Speculative Planning (Rule 4)</span>
        </div>
      </div>
    </div>
  );
};
