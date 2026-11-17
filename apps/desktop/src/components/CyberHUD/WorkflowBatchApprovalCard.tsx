import React, { useState, useEffect } from 'react';
import {
  Button,
  Badge,
  ProgressBar,
} from '@fluentui/react-components';
import {
  CheckmarkCircleRegular,
  DismissCircleRegular,
  WarningRegular,
  ClockRegular,
  ShieldRegular,
} from '@fluentui/react-icons';

export interface WorkflowStep {
  step_id: string;
  title: string;
  tool_name: string;
  args?: Record<string, any>;
  tier: number;
  depends_on?: string[];
  status: 'pending' | 'running' | 'completed' | 'failed' | 'diverged' | 'paused';
  output?: any;
  error?: string;
  divergence_reason?: string;
}

export interface WorkflowDAG {
  dag_id: string;
  goal: string;
  steps: WorkflowStep[];
  max_tier: number;
  estimated_duration_s: number;
  status: 'created' | 'approved' | 'executing' | 'completed' | 'failed' | 'aborted' | 'diverged';
  created_at?: number;
}

export interface WorkflowBatchApprovalCardProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const WorkflowBatchApprovalCard: React.FC<WorkflowBatchApprovalCardProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [dag, setDag] = useState<WorkflowDAG | null>(null);

  useEffect(() => {
    if (!externalEvent) return;
    const { type, payload } = externalEvent;

    if (type === 'WORKFLOW_DAG_CREATED') {
      setDag(payload as WorkflowDAG);
    } else if (type === 'WORKFLOW_DAG_APPROVED') {
      setDag((prev) => prev ? { ...prev, status: 'approved' } : null);
    } else if (type === 'WORKFLOW_STEP_STATUS') {
      setDag((prev) => {
        if (!prev) return null;
        const updated = prev.steps.map((s) =>
          s.step_id === payload.step_id
            ? { ...s, status: payload.status, output: payload.output, error: payload.error }
            : s
        );
        return { ...prev, steps: updated };
      });
    } else if (type === 'WORKFLOW_DIVERGENCE_ALERT') {
      setDag((prev) => {
        if (!prev) return null;
        const updated = prev.steps.map((s) =>
          s.step_id === payload.step_id
            ? { ...s, status: 'diverged' as const, divergence_reason: payload.reason }
            : s
        );
        return { ...prev, status: 'diverged', steps: updated };
      });
    } else if (type === 'WORKFLOW_EXECUTION_COMPLETED') {
      setDag((prev) => prev ? { ...prev, status: payload.status } : null);
    }
  }, [externalEvent]);

  if (!dag) return null;

  const handleApproveBatch = () => {
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'approve_workflow_batch',
          args: { dag_id: dag.dag_id },
        },
      });
      // Immediately trigger execution
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'execute_workflow_dag',
          args: { dag_id: dag.dag_id },
        },
      });
    }
  };

  const handleAbort = () => {
    setDag(null);
    if (onClose) onClose();
  };

  const completedSteps = dag.steps.filter((s) => s.status === 'completed').length;
  const progressPercent = dag.steps.length > 0 ? (completedSteps / dag.steps.length) * 100 : 0;

  return (
    <div
      style={{
        background: 'rgba(10, 13, 20, 0.95)',
        border: '1px solid rgba(0, 82, 255, 0.35)',
        borderRadius: 12,
        padding: '16px 20px',
        margin: '12px 0',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(16px)',
        color: '#f8fafc',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
      }}
    >
      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldRegular style={{ color: '#00e5ff', fontSize: 20 }} />
          <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: '0.04em', color: '#00e5ff' }}>
            AUTONOMOUS WORKFLOW DAG
          </span>
          <Badge
            appearance="filled"
            style={{
              background:
                dag.status === 'completed'
                  ? 'rgba(34, 197, 94, 0.2)'
                  : dag.status === 'diverged' || dag.status === 'failed'
                  ? 'rgba(239, 68, 68, 0.25)'
                  : 'rgba(0, 82, 255, 0.25)',
              color:
                dag.status === 'completed'
                  ? '#22c55e'
                  : dag.status === 'diverged' || dag.status === 'failed'
                  ? '#ef4444'
                  : '#3b82f6',
              border: '1px solid rgba(0, 82, 255, 0.3)',
            }}
          >
            {dag.status.toUpperCase()}
          </Badge>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 12, color: '#94a3b8' }}>
          <span>
            <ClockRegular style={{ verticalAlign: 'middle', marginRight: 4 }} />
            ~{dag.estimated_duration_s}s
          </span>
          <Badge
            appearance="tint"
            style={{
              background: dag.max_tier === 2 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
              color: dag.max_tier === 2 ? '#ef4444' : '#f59e0b',
            }}
          >
            Max Tier {dag.max_tier}
          </Badge>
          <Button
            size="small"
            appearance="subtle"
            icon={<DismissCircleRegular />}
            onClick={handleAbort}
          />
        </div>
      </div>

      {/* Goal Title */}
      <div style={{ fontSize: 13, color: '#e2e8f0', marginBottom: 12, fontWeight: 500 }}>
        <strong style={{ color: '#CCFF00' }}>Goal:</strong> {dag.goal}
      </div>

      {/* Progress Bar if executing/completed */}
      {dag.status !== 'created' && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#64748b', marginBottom: 4 }}>
            <span>Execution Progress</span>
            <span>{completedSteps} / {dag.steps.length} Steps Completed</span>
          </div>
          <ProgressBar value={progressPercent / 100} color={dag.status === 'failed' ? 'error' : 'success'} />
        </div>
      )}

      {/* Divergence Alert Banner */}
      {dag.status === 'diverged' && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid #ef4444',
            borderRadius: 8,
            padding: '10px 14px',
            marginBottom: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            color: '#fca5a5',
            fontSize: 12,
          }}
        >
          <WarningRegular style={{ color: '#ef4444', fontSize: 18 }} />
          <div>
            <strong>Divergence Guard Paused Execution:</strong> Pre-condition verification failed. The physical environment state deviated from expected.
          </div>
        </div>
      )}

      {/* Step Sequence List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 220, overflowY: 'auto', marginBottom: 16 }}>
        {dag.steps.map((step, idx) => (
          <div
            key={step.step_id}
            style={{
              background: 'rgba(15, 23, 42, 0.65)',
              border: `1px solid ${
                step.status === 'completed'
                  ? 'rgba(34, 197, 94, 0.4)'
                  : step.status === 'running'
                  ? '#00e5ff'
                  : step.status === 'diverged'
                  ? '#ef4444'
                  : 'rgba(51, 65, 85, 0.5)'
              }`,
              borderRadius: 8,
              padding: '8px 12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: 12,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontWeight: 700, color: '#64748b', width: 16 }}>{idx + 1}</span>
              <span style={{ fontWeight: 600, color: '#f1f5f9' }}>{step.title}</span>
              <span style={{ color: '#00e5ff', fontFamily: 'Consolas, monospace', fontSize: 11 }}>
                ({step.tool_name})
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Badge
                appearance="tint"
                size="small"
                style={{
                  background: step.tier === 0 ? 'rgba(59, 130, 246, 0.15)' : step.tier === 1 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: step.tier === 0 ? '#60a5fa' : step.tier === 1 ? '#fbbf24' : '#f87171',
                }}
              >
                T{step.tier}
              </Badge>
              <Badge
                appearance="filled"
                size="small"
                style={{
                  background:
                    step.status === 'completed'
                      ? 'rgba(34, 197, 94, 0.2)'
                      : step.status === 'running'
                      ? 'rgba(0, 229, 255, 0.2)'
                      : step.status === 'diverged'
                      ? 'rgba(239, 68, 68, 0.25)'
                      : 'rgba(51, 65, 85, 0.4)',
                  color:
                    step.status === 'completed'
                      ? '#4ade80'
                      : step.status === 'running'
                      ? '#38bdf8'
                      : step.status === 'diverged'
                      ? '#f87171'
                      : '#94a3b8',
                }}
              >
                {step.status}
              </Badge>
            </div>
          </div>
        ))}
      </div>

      {/* Action Footer */}
      {dag.status === 'created' && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <Button appearance="secondary" size="small" onClick={handleAbort}>
            Cancel Plan
          </Button>
          <Button
            appearance="primary"
            size="small"
            icon={<CheckmarkCircleRegular />}
            style={{ background: '#0052FF', color: '#ffffff' }}
            onClick={handleApproveBatch}
          >
            1-Click Batch Approve & Execute
          </Button>
        </div>
      )}
    </div>
  );
};
export default WorkflowBatchApprovalCard;
