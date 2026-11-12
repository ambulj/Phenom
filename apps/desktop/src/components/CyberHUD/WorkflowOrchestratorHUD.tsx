import React, { useState } from 'react';
import {
  DismissRegular,
  PlayRegular,
  ArrowResetRegular,
  CheckmarkCircleRegular,
  DismissCircleRegular,
  ClockRegular,
  BranchForkRegular,
  DesktopRegular,
  DocumentRegular,
  CodeRegular,
} from '@fluentui/react-icons';

export interface WorkflowOrchestratorHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

interface StepUI {
  id: string;
  name: string;
  action_type: 'SHELL_COMMAND' | 'FILE_OPERATION' | 'OBSIDIAN_NOTE' | 'BROWSER_ACTION' | 'DESKTOP_GUI';
  target_app: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'ROLLED_BACK';
  pre_check?: string;
  post_check?: string;
  duration_ms?: number;
  output_preview?: string;
}

export const WorkflowOrchestratorHUD: React.FC<WorkflowOrchestratorHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [activeWorkflow, setActiveWorkflow] = useState<{
    id: string;
    name: string;
    description: string;
    status: 'CREATED' | 'RUNNING' | 'COMPLETED' | 'ROLLED_BACK';
    variables: Record<string, string>;
  }>({
    id: 'wf-prod-morning-sync',
    name: 'Morning Cross-App Automation Suite',
    description: 'Chained cross-application workflow coordinating Terminal, Obsidian, and Browser with state verification.',
    status: 'RUNNING',
    variables: {
      project_root: 'C:\\Phenom',
      daily_note: 'Daily/2026-11-12',
      dev_port: '5173',
    },
  });

  const [steps, setSteps] = useState<StepUI[]>([
    {
      id: 'step-1',
      name: 'Git Status & Branch Verification',
      action_type: 'SHELL_COMMAND',
      target_app: 'terminal',
      status: 'COMPLETED',
      pre_check: 'File exists (package.json)',
      post_check: 'Exit code 0',
      duration_ms: 45.2,
      output_preview: 'On branch hardening/pass-1, clean working tree',
    },
    {
      id: 'step-2',
      name: 'Pytest Suite Execution',
      action_type: 'SHELL_COMMAND',
      target_app: 'terminal',
      status: 'COMPLETED',
      pre_check: 'Python 3.11 installed',
      post_check: 'Exit code 0',
      duration_ms: 820.5,
      output_preview: '62 passed in 1.85s',
    },
    {
      id: 'step-3',
      name: 'Obsidian Daily Note Digest Log',
      action_type: 'OBSIDIAN_NOTE',
      target_app: 'obsidian',
      status: 'RUNNING',
      pre_check: 'Vault accessible',
      post_check: 'File updated',
      output_preview: 'Staging automated morning report in vault/Daily/2026-11-12.md...',
    },
    {
      id: 'step-4',
      name: 'Launch Desktop Dashboard',
      action_type: 'BROWSER_ACTION',
      target_app: 'browser',
      status: 'PENDING',
      pre_check: 'Port 5173 responsive',
      post_check: 'Window title contains Phenom',
    },
  ]);

  const handleExecuteNext = () => {
    setSteps((prev) => {
      const nextSteps = [...prev];
      const runningIdx = nextSteps.findIndex((s) => s.status === 'RUNNING');
      if (runningIdx !== -1) {
        nextSteps[runningIdx].status = 'COMPLETED';
        nextSteps[runningIdx].duration_ms = 120.4;
        nextSteps[runningIdx].output_preview = 'Summary crystallized into vault successfully.';
        if (runningIdx + 1 < nextSteps.length) {
          nextSteps[runningIdx + 1].status = 'RUNNING';
        } else {
          setActiveWorkflow((w) => ({ ...w, status: 'COMPLETED' }));
        }
      } else {
        const pendingIdx = nextSteps.findIndex((s) => s.status === 'PENDING');
        if (pendingIdx !== -1) {
          nextSteps[pendingIdx].status = 'RUNNING';
        }
      }
      return nextSteps;
    });
  };

  const handleRollback = () => {
    setSteps((prev) =>
      prev.map((s) =>
        s.status === 'COMPLETED' || s.status === 'RUNNING'
          ? { ...s, status: 'ROLLED_BACK', output_preview: 'Compensatory rollback executed.' }
          : s
      )
    );
    setActiveWorkflow((w) => ({ ...w, status: 'ROLLED_BACK' }));
  };

  const handleReset = () => {
    setSteps((prev) =>
      prev.map((s, idx) => ({
        ...s,
        status: idx === 0 ? 'RUNNING' : 'PENDING',
        duration_ms: undefined,
        output_preview: undefined,
      }))
    );
    setActiveWorkflow((w) => ({ ...w, status: 'RUNNING' }));
  };

  const getAppIcon = (app: string) => {
    switch (app.toLowerCase()) {
      case 'terminal':
        return <CodeRegular style={{ color: '#00f0ff' }} />;
      case 'obsidian':
        return <DocumentRegular style={{ color: '#a855f7' }} />;
      case 'browser':
        return <DesktopRegular style={{ color: '#10b981' }} />;
      default:
        return <BranchForkRegular style={{ color: '#f59e0b' }} />;
    }
  };

  const getStatusBadge = (status: StepUI['status']) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
            <CheckmarkCircleRegular /> COMPLETED
          </span>
        );
      case 'RUNNING':
        return (
          <span style={{ color: '#00f0ff', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
            <ClockRegular /> RUNNING
          </span>
        );
      case 'FAILED':
        return (
          <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
            <DismissCircleRegular /> FAILED
          </span>
        );
      case 'ROLLED_BACK':
        return (
          <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
            <ArrowResetRegular /> ROLLED BACK
          </span>
        );
      default:
        return (
          <span style={{ color: '#6b7280', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
            <ClockRegular /> PENDING
          </span>
        );
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: '60px',
        right: '20px',
        width: '560px',
        maxHeight: '85vh',
        background: 'rgba(10, 15, 29, 0.92)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 240, 255, 0.25)',
        borderRadius: '12px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 24px rgba(0, 240, 255, 0.15)',
        color: '#e2e8f0',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid rgba(0, 240, 255, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BranchForkRegular style={{ fontSize: '20px', color: '#00f0ff' }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: '14px', letterSpacing: '0.5px' }}>
              Workflow Orchestrator HUD
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>FLOW-01 / CHAIN-02 Cross-App DAG Engine</div>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
            }}
          >
            <DismissRegular style={{ fontSize: '18px' }} />
          </button>
        )}
      </div>

      {/* Body */}
      <div style={{ padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Workflow Overview Card */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(0, 240, 255, 0.2)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontWeight: 600, fontSize: '13px', color: '#00f0ff' }}>{activeWorkflow.name}</span>
            <span
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '4px',
                background:
                  activeWorkflow.status === 'COMPLETED'
                    ? 'rgba(16, 185, 129, 0.2)'
                    : activeWorkflow.status === 'ROLLED_BACK'
                    ? 'rgba(245, 158, 11, 0.2)'
                    : 'rgba(0, 240, 255, 0.2)',
                color:
                  activeWorkflow.status === 'COMPLETED'
                    ? '#10b981'
                    : activeWorkflow.status === 'ROLLED_BACK'
                    ? '#f59e0b'
                    : '#00f0ff',
              }}
            >
              {activeWorkflow.status}
            </span>
          </div>
          <div style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '8px' }}>
            {activeWorkflow.description}
          </div>

          {/* Variables Bar */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {Object.entries(activeWorkflow.variables).map(([k, v]) => (
              <span
                key={k}
                style={{
                  fontSize: '10px',
                  background: 'rgba(255, 255, 255, 0.05)',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  color: '#94a3b8',
                }}
              >
                <strong style={{ color: '#38bdf8' }}>{k}:</strong> {v}
              </span>
            ))}
          </div>
        </div>

        {/* Step Nodes DAG Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Execution DAG Steps ({steps.length})
          </div>

          {steps.map((step, idx) => (
            <div
              key={step.id}
              style={{
                background:
                  step.status === 'RUNNING'
                    ? 'rgba(0, 240, 255, 0.08)'
                    : step.status === 'COMPLETED'
                    ? 'rgba(16, 185, 129, 0.05)'
                    : 'rgba(255, 255, 255, 0.02)',
                border:
                  step.status === 'RUNNING'
                    ? '1px solid #00f0ff'
                    : '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '12px',
                position: 'relative',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {getAppIcon(step.target_app)}
                  <span style={{ fontWeight: 600, fontSize: '13px' }}>
                    {idx + 1}. {step.name}
                  </span>
                </div>
                {getStatusBadge(step.status)}
              </div>

              {/* Checkpoints info */}
              <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                {step.pre_check && (
                  <span>
                    <strong>Pre:</strong> {step.pre_check}
                  </span>
                )}
                {step.post_check && (
                  <span>
                    <strong>Post:</strong> {step.post_check}
                  </span>
                )}
                {step.duration_ms && (
                  <span style={{ marginLeft: 'auto', color: '#38bdf8' }}>
                    {step.duration_ms.toFixed(1)}ms
                  </span>
                )}
              </div>

              {step.output_preview && (
                <div
                  style={{
                    marginTop: '8px',
                    padding: '6px 8px',
                    background: 'rgba(0, 0, 0, 0.3)',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontFamily: 'monospace',
                    color: '#a5f3fc',
                  }}
                >
                  {step.output_preview}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Footer Controls */}
      <div
        style={{
          padding: '12px 18px',
          borderTop: '1px solid rgba(0, 240, 255, 0.15)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(15, 23, 42, 0.8)',
        }}
      >
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleExecuteNext}
            style={{
              background: '#00f0ff',
              color: '#0a0f1d',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 14px',
              fontWeight: 600,
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
            }}
          >
            <PlayRegular /> Execute Next Step
          </button>
          <button
            onClick={handleRollback}
            style={{
              background: 'rgba(245, 158, 11, 0.15)',
              color: '#f59e0b',
              border: '1px solid #f59e0b',
              borderRadius: '6px',
              padding: '6px 12px',
              fontWeight: 600,
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
            }}
          >
            <ArrowResetRegular /> Rollback DAG
          </button>
        </div>

        <button
          onClick={handleReset}
          style={{
            background: 'transparent',
            color: '#94a3b8',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '6px',
            padding: '6px 10px',
            fontSize: '12px',
            cursor: 'pointer',
          }}
        >
          Reset
        </button>
      </div>
    </div>
  );
};
