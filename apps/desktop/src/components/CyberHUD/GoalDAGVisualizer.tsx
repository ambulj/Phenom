import React, { useState } from 'react';
import {
  BranchForkRegular,
  CheckmarkCircleRegular,
  DismissCircleRegular,
  ArrowCounterclockwiseRegular,
  StopRegular,
  PlayRegular,
  DismissRegular,
  WarningRegular,
} from '@fluentui/react-icons';
import {
  GoalDAGPayload,
  DAGNodePayload,
  DAGBranchPayload,
  DAGNodeStatus,
} from '../../types/protocol';

export interface GoalDAGVisualizerProps {
  dag: GoalDAGPayload | null;
  onPruneBranch?: (branchId: string, reason?: string) => void;
  onAbortGoal?: (reason?: string) => void;
  onResumeGoal?: () => void;
  onExecuteStep?: (nodeId?: string) => void;
}

export const GoalDAGVisualizer: React.FC<GoalDAGVisualizerProps> = ({
  dag,
  onPruneBranch,
  onAbortGoal,
  onExecuteStep,
}) => {
  const [selectedBranchId, setSelectedBranchId] = useState<string | null>(null);

  if (!dag) {
    return (
      <div
        style={{
          background: 'rgba(15, 23, 42, 0.75)',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          borderRadius: 12,
          padding: '20px',
          color: '#94A3B8',
          fontFamily: "'Segoe UI', -apple-system, sans-serif",
          textAlign: 'center',
          backdropFilter: 'blur(12px)',
        }}
      >
        <BranchForkRegular style={{ fontSize: 32, color: '#38BDF8', marginBottom: 8 }} />
        <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.05em' }}>
          TREE-OF-THOUGHT GOAL ENGINE IDLE
        </div>
        <div style={{ fontSize: 11, color: '#64748B', marginTop: 4 }}>
          No active hierarchical Goal DAG in execution context.
        </div>
      </div>
    );
  }

  const activeBranchId = dag.active_branch_id;
  const currentViewBranchId = selectedBranchId || activeBranchId;
  const activeBranch: DAGBranchPayload | undefined = dag.branches[currentViewBranchId];
  const branchNodes: DAGNodePayload[] = activeBranch
    ? activeBranch.node_ids.map((id) => dag.nodes[id]).filter(Boolean)
    : [];

  const getStatusBadge = (status: DAGNodeStatus) => {
    switch (status) {
      case 'COMPLETED':
        return { color: '#00FF9D', bg: 'rgba(0, 255, 157, 0.15)', border: '#00FF9D', icon: <CheckmarkCircleRegular /> };
      case 'RUNNING':
        return { color: '#00E5FF', bg: 'rgba(0, 229, 255, 0.2)', border: '#00E5FF', icon: <PlayRegular /> };
      case 'FAILED':
        return { color: '#EF4444', bg: 'rgba(239, 68, 68, 0.2)', border: '#EF4444', icon: <DismissCircleRegular /> };
      case 'PRUNED':
        return { color: '#71717A', bg: 'rgba(113, 113, 122, 0.2)', border: '#71717A', icon: <DismissRegular /> };
      case 'ROLLED_BACK':
        return { color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.2)', border: '#F59E0B', icon: <ArrowCounterclockwiseRegular /> };
      default:
        return { color: '#94A3B8', bg: 'rgba(148, 163, 184, 0.15)', border: '#64748B', icon: <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#94A3B8' }} /> };
    }
  };

  return (
    <div
      style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(10, 15, 30, 0.9) 100%)',
        border: '1.5px solid #00E5FF',
        borderRadius: 12,
        padding: '20px',
        boxShadow: '0 0 25px rgba(0, 229, 255, 0.25), inset 0 0 15px rgba(0, 229, 255, 0.05)',
        backdropFilter: 'blur(16px)',
        color: '#F8FAFC',
        fontFamily: "'Segoe UI', -apple-system, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        margin: '12px 0',
      }}
    >
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: 'rgba(0, 229, 255, 0.15)',
              border: '1px solid #00E5FF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 10px rgba(0, 229, 255, 0.4)',
            }}
          >
            <BranchForkRegular style={{ color: '#00E5FF', fontSize: 20 }} />
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#00E5FF', letterSpacing: '0.08em' }}>
              HIERARCHICAL TREE-OF-THOUGHT GOAL ENGINE
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#FFFFFF', marginTop: 2 }}>
              {dag.goal_description}
            </div>
          </div>
        </div>

        {/* Status Badge */}
        <div
          style={{
            padding: '4px 10px',
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.05em',
            background: dag.status === 'COMPLETED' ? 'rgba(0, 255, 157, 0.2)' : 'rgba(0, 229, 255, 0.2)',
            border: `1px solid ${dag.status === 'COMPLETED' ? '#00FF9D' : '#00E5FF'}`,
            color: dag.status === 'COMPLETED' ? '#00FF9D' : '#00E5FF',
          }}
        >
          {dag.status}
        </div>
      </div>

      {/* Progress Bar */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94A3B8', marginBottom: 6 }}>
          <span>Execution Progress</span>
          <span style={{ color: '#00E5FF', fontWeight: 600 }}>{dag.overall_progress_pct}%</span>
        </div>
        <div style={{ height: 6, background: 'rgba(255, 255, 255, 0.08)', borderRadius: 3, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${Math.min(100, Math.max(0, dag.overall_progress_pct))}%`,
              background: 'linear-gradient(90deg, #00E5FF 0%, #00FF9D 100%)',
              boxShadow: '0 0 8px rgba(0, 229, 255, 0.6)',
              transition: 'width 0.4s ease',
            }}
          />
        </div>
      </div>

      {/* Branch Selector Tabs */}
      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
        {Object.values(dag.branches).map((branch) => {
          const isSelected = branch.branch_id === currentViewBranchId;
          const isActive = branch.branch_id === activeBranchId;
          return (
            <button
              key={branch.branch_id}
              onClick={() => setSelectedBranchId(branch.branch_id)}
              style={{
                background: isSelected ? 'rgba(0, 229, 255, 0.2)' : 'rgba(30, 41, 59, 0.6)',
                border: isSelected ? '1px solid #00E5FF' : '1px solid rgba(148, 163, 184, 0.2)',
                borderRadius: 8,
                padding: '6px 12px',
                color: isSelected ? '#FFFFFF' : '#94A3B8',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                transition: 'all 0.2s',
              }}
            >
              <span>{branch.name}</span>
              {isActive && (
                <span
                  style={{
                    background: '#00FF9D',
                    color: '#0A0F1D',
                    fontSize: 9,
                    fontWeight: 700,
                    borderRadius: 4,
                    padding: '1px 4px',
                  }}
                >
                  ACTIVE
                </span>
              )}
              {branch.pruned && (
                <span
                  style={{
                    background: '#EF4444',
                    color: '#FFFFFF',
                    fontSize: 9,
                    fontWeight: 700,
                    borderRadius: 4,
                    padding: '1px 4px',
                  }}
                >
                  PRUNED
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Node Topology List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {branchNodes.map((node, index) => {
          const badge = getStatusBadge(node.status);
          return (
            <div
              key={node.node_id}
              style={{
                background: 'rgba(30, 41, 59, 0.5)',
                border: `1px solid ${node.status === 'RUNNING' ? '#00E5FF' : 'rgba(148, 163, 184, 0.15)'}`,
                borderRadius: 8,
                padding: '10px 14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontSize: 11, color: '#64748B', fontFamily: 'monospace', width: 20 }}>
                  #{index + 1}
                </span>
                <div
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    background: badge.bg,
                    border: `1px solid ${badge.border}`,
                    color: badge.color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 14,
                  }}
                >
                  {badge.icon}
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>
                    {node.title}
                  </div>
                  <div style={{ fontSize: 11, color: '#94A3B8' }}>
                    {node.description}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span
                  style={{
                    fontSize: 10,
                    padding: '2px 6px',
                    borderRadius: 4,
                    background: 'rgba(56, 189, 248, 0.1)',
                    border: '1px solid rgba(56, 189, 248, 0.3)',
                    color: '#38BDF8',
                    fontFamily: 'monospace',
                  }}
                >
                  Tier {node.tier}
                </span>
                <span
                  style={{
                    fontSize: 10,
                    padding: '2px 6px',
                    borderRadius: 4,
                    background: badge.bg,
                    border: `1px solid ${badge.border}`,
                    color: badge.color,
                    fontWeight: 600,
                  }}
                >
                  {node.status}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Control Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4, paddingTop: 12, borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <div style={{ display: 'flex', gap: 8 }}>
          {onExecuteStep && dag.status !== 'COMPLETED' && (
            <button
              onClick={() => onExecuteStep()}
              style={{
                background: 'linear-gradient(135deg, #00E5FF 0%, #00B4D8 100%)',
                border: 'none',
                borderRadius: 6,
                padding: '6px 14px',
                color: '#0A0F1D',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <PlayRegular style={{ fontSize: 14 }} />
              Execute Step
            </button>
          )}

          {onPruneBranch && activeBranch && !activeBranch.pruned && (
            <button
              onClick={() => onPruneBranch(activeBranch.branch_id, 'User requested manual pruning')}
              style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: 6,
                padding: '6px 12px',
                color: '#EF4444',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <WarningRegular style={{ fontSize: 14 }} />
              Prune Branch
            </button>
          )}
        </div>

        {onAbortGoal && dag.status !== 'ABORTED' && dag.status !== 'COMPLETED' && (
          <button
            onClick={() => onAbortGoal('Aborted via Cyber HUD')}
            style={{
              background: 'rgba(113, 113, 122, 0.2)',
              border: '1px solid rgba(113, 113, 122, 0.4)',
              borderRadius: 6,
              padding: '6px 12px',
              color: '#CBD5E1',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <StopRegular style={{ fontSize: 14 }} />
            Abort Goal
          </button>
        )}
      </div>
    </div>
  );
};
