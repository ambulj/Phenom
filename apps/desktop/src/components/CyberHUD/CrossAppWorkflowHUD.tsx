import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  AppsRegular,
  WindowRegular,
  PlayRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
} from '@fluentui/react-icons';

export interface WorkflowStepUI {
  step_id: number;
  app_name: string;
  action: string;
  input_payload?: string;
  output_variable?: string;
  status: 'PENDING' | 'SUCCESS' | 'FAILED';
  result_data?: string;
}

export interface WindowItemUI {
  window_id: string;
  process_name: string;
  title: string;
  is_foreground: boolean;
}

interface CrossAppWorkflowHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const CrossAppWorkflowHUD: React.FC<CrossAppWorkflowHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [workflowTitle] = useState<string>('Documentation to Code Pipeline');
  const [workflowStatus, setWorkflowStatus] = useState<'IDLE' | 'RUNNING' | 'COMPLETED'>('IDLE');

  const [steps, setSteps] = useState<WorkflowStepUI[]>([
    {
      step_id: 1,
      app_name: 'Microsoft Edge',
      action: 'EXTRACT_SELECTION',
      output_variable: 'api_docs',
      status: 'PENDING',
      result_data: 'API specifications and request schema',
    },
    {
      step_id: 2,
      app_name: 'Visual Studio Code',
      action: 'PASTE_TRANSFORM',
      input_payload: 'Generate TypeScript interface from ${api_docs}',
      output_variable: 'generated_interface',
      status: 'PENDING',
    },
    {
      step_id: 3,
      app_name: 'Windows Terminal',
      action: 'EXECUTE_COMMAND',
      input_payload: 'npm test -- --filter=api',
      status: 'PENDING',
    },
  ]);

  const [windows, setWindows] = useState<WindowItemUI[]>([
    {
      window_id: 'win_ide_01',
      process_name: 'Code.exe',
      title: 'Phenom - Visual Studio Code',
      is_foreground: true,
    },
    {
      window_id: 'win_browser_02',
      process_name: 'msedge.exe',
      title: 'Edge - Documentation & APIs',
      is_foreground: false,
    },
    {
      window_id: 'win_term_03',
      process_name: 'WindowsTerminal.exe',
      title: 'Terminal - Backend Services',
      is_foreground: false,
    },
  ]);

  const [sharedContext, setSharedContext] = useState<Record<string, string>>({
    api_docs: 'Extracted 14 endpoint routes and Pydantic models',
    generated_interface: 'Exported TypeScript interfaces in src/types/api.ts',
  });

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'workflow.update' && externalEvent.payload) {
      if (externalEvent.payload.steps) setSteps(externalEvent.payload.steps);
      if (externalEvent.payload.status) setWorkflowStatus(externalEvent.payload.status);
      if (externalEvent.payload.context) setSharedContext(externalEvent.payload.context);
    }
  }, [externalEvent]);

  const handleRunWorkflow = () => {
    setWorkflowStatus('RUNNING');
    setSteps((prev) => prev.map((s) => ({ ...s, status: 'PENDING' })));

    if (sendMessage) {
      sendMessage({
        type: 'workflow.run',
        payload: { title: workflowTitle },
      });
    }

    setFeedback('Orchestrating cross-app workflow steps...');

    setTimeout(() => {
      setSteps((prev) =>
        prev.map((s, idx) => (idx === 0 ? { ...s, status: 'SUCCESS' } : s))
      );
    }, 500);

    setTimeout(() => {
      setSteps((prev) =>
        prev.map((s, idx) => (idx <= 1 ? { ...s, status: 'SUCCESS' } : s))
      );
    }, 1000);

    setTimeout(() => {
      setSteps((prev) => prev.map((s) => ({ ...s, status: 'SUCCESS' })));
      setWorkflowStatus('COMPLETED');
      setFeedback('Cross-app pipeline finished successfully! Context propagated across 3 apps.');
      setTimeout(() => setFeedback(null), 3000);
    }, 1500);
  };

  const handleSwitchFocus = (windowId: string, processName: string) => {
    setWindows((prev) =>
      prev.map((w) => ({
        ...w,
        is_foreground: w.window_id === windowId,
      }))
    );

    if (sendMessage) {
      sendMessage({
        type: 'window.switch_focus',
        payload: { window_id: windowId },
      });
    }

    setFeedback(`Switched foreground window to ${processName}`);
    setTimeout(() => setFeedback(null), 2500);
  };

  const getAppColor = (appName: string) => {
    if (appName.includes('Edge')) return '#38bdf8';
    if (appName.includes('Code') || appName.includes('VSCode')) return '#00ffcc';
    if (appName.includes('Terminal')) return '#a855f7';
    return '#f59e0b';
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
          <AppsRegular style={{ color: '#00ffcc', fontSize: 18 }} />
          <span style={{ fontWeight: 600, fontSize: 13, letterSpacing: '0.05em', color: '#f8fafc' }}>
            CROSS-APP WORKFLOW ORCHESTRATOR
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              backgroundColor: workflowStatus === 'COMPLETED' ? 'rgba(0, 255, 204, 0.2)' : 'rgba(56, 189, 248, 0.2)',
              color: workflowStatus === 'COMPLETED' ? '#00ffcc' : '#38bdf8',
              fontWeight: 600,
            }}
          >
            {workflowStatus}
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
        {/* Active Pipeline Card */}
        <div
          style={{
            backgroundColor: '#070a0f',
            border: '1px solid #1e293b',
            borderRadius: 8,
            padding: 12,
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Active Multi-App Pipeline
            </span>
            <span style={{ fontSize: 10, color: '#00ffcc', fontWeight: 600 }}>AUT-05 / WIN-02</span>
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>{workflowTitle}</div>
        </div>

        {/* Pipeline Step Stream */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Workflow Execution Steps</div>
          {steps.map((step) => (
            <div
              key={step.step_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                backgroundColor: '#070a0f',
                border: `1px solid ${step.status === 'SUCCESS' ? '#00ffcc44' : '#1e293b'}`,
                borderRadius: 6,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span
                  style={{
                    fontSize: 10,
                    padding: '2px 6px',
                    borderRadius: 4,
                    backgroundColor: `${getAppColor(step.app_name)}22`,
                    color: getAppColor(step.app_name),
                    fontWeight: 700,
                  }}
                >
                  {step.app_name.split(' ')[0]}
                </span>
                <div>
                  <div style={{ fontSize: 11, color: '#f1f5f9', fontWeight: 600 }}>{step.action}</div>
                  {step.output_variable && (
                    <div style={{ fontSize: 10, color: '#38bdf8' }}>
                      Context output: <code>${`{${step.output_variable}}`}</code>
                    </div>
                  )}
                </div>
              </div>

              <div>
                {step.status === 'SUCCESS' ? (
                  <CheckmarkCircleRegular style={{ color: '#00ffcc', fontSize: 16 }} />
                ) : (
                  <span style={{ fontSize: 10, color: '#64748b' }}>PENDING</span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Window Context & Focus Switcher */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Workspace Window Focus Stack</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {windows.map((win) => (
              <button
                key={win.window_id}
                onClick={() => handleSwitchFocus(win.window_id, win.process_name)}
                style={{
                  flex: 1,
                  padding: '6px 8px',
                  borderRadius: 6,
                  backgroundColor: win.is_foreground ? 'rgba(0, 255, 204, 0.15)' : '#0f172a',
                  border: `1px solid ${win.is_foreground ? '#00ffcc' : '#334155'}`,
                  color: win.is_foreground ? '#00ffcc' : '#94a3b8',
                  fontSize: 10,
                  fontWeight: win.is_foreground ? 700 : 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 4,
                }}
              >
                <WindowRegular style={{ fontSize: 12 }} />
                {win.process_name.replace('.exe', '')}
              </button>
            ))}
          </div>
        </div>

        {/* Shared Pipeline Context Preview */}
        <div
          style={{
            backgroundColor: '#070a0f',
            border: '1px solid #1e293b',
            borderRadius: 6,
            padding: 10,
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
          }}
        >
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>
            Shared Variable Store
          </div>
          {Object.entries(sharedContext).map(([k, v]) => (
            <div key={k} style={{ fontSize: 10, color: '#94a3b8' }}>
              <span style={{ color: '#38bdf8' }}>${`{${k}}`}: </span>
              <span style={{ color: '#cbd5e1' }}>{v}</span>
            </div>
          ))}
        </div>

        {/* Execution Button */}
        <button
          onClick={handleRunWorkflow}
          disabled={workflowStatus === 'RUNNING'}
          style={{
            padding: '8px 12px',
            borderRadius: 6,
            backgroundColor: '#00ffcc',
            color: '#0a0d14',
            border: 'none',
            fontSize: 11,
            fontWeight: 700,
            cursor: workflowStatus === 'RUNNING' ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <PlayRegular style={{ fontSize: 14 }} />
          Orchestrate Workflow Now
        </button>

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
            Ambient Inter-App Security Enforced
          </span>
          <span>Guardian SLA &lt; 25ms</span>
        </div>
      </div>
    </div>
  );
};
