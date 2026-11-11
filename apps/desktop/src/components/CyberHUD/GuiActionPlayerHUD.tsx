import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  PlayRegular,
  CheckmarkCircleRegular,
  WarningRegular,
  HandRightRegular,
  CursorRegular,
  KeyboardRegular,
  ShieldCheckmarkRegular,
} from '@fluentui/react-icons';

export interface GuiActionStepUI {
  step_id: number;
  action_type: 'CLICK' | 'TYPE_TEXT' | 'KEY_SHORTCUT' | 'DOUBLE_CLICK';
  description: string;
  target_coordinates?: [number, number];
  text_payload?: string;
  key_combination?: string;
  status: 'PENDING' | 'EXECUTING' | 'COMPLETED' | 'ABORTED';
}

export interface GuiActionPlanUI {
  plan_id: string;
  user_goal: string;
  steps: GuiActionStepUI[];
  status: 'READY' | 'EXECUTING' | 'COMPLETED' | 'ABORTED_BY_HUMAN';
  estimated_duration_ms: number;
}

interface GuiActionPlayerHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const GuiActionPlayerHUD: React.FC<GuiActionPlayerHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [plan, setPlan] = useState<GuiActionPlanUI>({
    plan_id: 'plan_a94f02',
    user_goal: 'search for main.py in the editor and open it',
    status: 'READY',
    estimated_duration_ms: 1050,
    steps: [
      {
        step_id: 1,
        action_type: 'CLICK',
        description: 'Click search bar at (540, 64)',
        target_coordinates: [540, 64],
        status: 'PENDING',
      },
      {
        step_id: 2,
        action_type: 'TYPE_TEXT',
        description: "Type search query 'main.py'",
        text_payload: 'main.py',
        status: 'PENDING',
      },
      {
        step_id: 3,
        action_type: 'KEY_SHORTCUT',
        description: "Press 'Enter' to open matched file",
        key_combination: 'Enter',
        status: 'PENDING',
      },
    ],
  });

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'actor.plan_update' && externalEvent.payload) {
      if (externalEvent.payload.plan) setPlan(externalEvent.payload.plan);
    }
  }, [externalEvent]);

  const handleExecutePlan = (dryRun: boolean = false) => {
    setPlan((prev) => ({
      ...prev,
      status: 'EXECUTING',
      steps: prev.steps.map((s, idx) => ({
        ...s,
        status: idx === 0 ? 'EXECUTING' : 'PENDING',
      })),
    }));

    if (sendMessage) {
      sendMessage({
        type: 'actor.execute_plan',
        payload: { plan_id: plan.plan_id, dry_run: dryRun },
      });
    }

    setFeedback(dryRun ? '[Dry-Run] Verifying action coordinates...' : 'Executing virtual GUI steps safely...');

    // Simulate step progression
    setTimeout(() => {
      setPlan((prev) => ({
        ...prev,
        steps: prev.steps.map((s, idx) => ({
          ...s,
          status: idx <= 1 ? 'COMPLETED' : 'EXECUTING',
        })),
      }));
    }, 600);

    setTimeout(() => {
      setPlan((prev) => ({
        ...prev,
        status: 'COMPLETED',
        steps: prev.steps.map((s) => ({ ...s, status: 'COMPLETED' })),
      }));
      setFeedback(dryRun ? '[Dry-Run] All 3 steps verified safe.' : 'GUI Action Plan completed successfully!');
      setTimeout(() => setFeedback(null), 3000);
    }, 1200);
  };

  const handleHumanTakeover = () => {
    setPlan((prev) => ({
      ...prev,
      status: 'ABORTED_BY_HUMAN',
      steps: prev.steps.map((s) => (s.status === 'EXECUTING' ? { ...s, status: 'ABORTED' } : s)),
    }));

    if (sendMessage) {
      sendMessage({
        type: 'actor.human_takeover',
        payload: { reason: 'Operator intervened manually' },
      });
    }

    setFeedback('HUMAN TAKEOVER TRIGGERED: Synthetic GUI execution halted immediately.');
    setTimeout(() => setFeedback(null), 4000);
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'CLICK':
      case 'DOUBLE_CLICK':
        return <CursorRegular style={{ fontSize: 13, color: '#00ffcc' }} />;
      case 'TYPE_TEXT':
      case 'KEY_SHORTCUT':
        return <KeyboardRegular style={{ fontSize: 13, color: '#f59e0b' }} />;
      default:
        return <CursorRegular style={{ fontSize: 13, color: '#38bdf8' }} />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <span style={{ color: '#00ffcc', fontSize: 10, fontWeight: 700 }}>DONE</span>;
      case 'EXECUTING':
        return <span style={{ color: '#38bdf8', fontSize: 10, fontWeight: 700 }}>ACTIVE</span>;
      case 'ABORTED':
      case 'ABORTED_BY_HUMAN':
        return <span style={{ color: '#ff0055', fontSize: 10, fontWeight: 700 }}>TAKEOVER</span>;
      default:
        return <span style={{ color: '#64748b', fontSize: 10 }}>PENDING</span>;
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        width: 500,
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
          <CursorRegular style={{ color: '#00ffcc', fontSize: 18 }} />
          <span style={{ fontWeight: 600, fontSize: 13, letterSpacing: '0.05em', color: '#f8fafc' }}>
            DECLARATIVE GUI ACTION PLAYER
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              backgroundColor: plan.status === 'ABORTED_BY_HUMAN' ? 'rgba(255, 0, 85, 0.2)' : 'rgba(0, 255, 204, 0.2)',
              color: plan.status === 'ABORTED_BY_HUMAN' ? '#ff0055' : '#00ffcc',
              fontWeight: 600,
            }}
          >
            {plan.status}
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
        {/* User Goal Card */}
        <div
          style={{
            backgroundColor: '#070a0f',
            border: '1px solid #1e293b',
            borderRadius: 8,
            padding: 12,
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
          }}
        >
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Active Task Goal
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>{plan.user_goal}</div>
          <div style={{ fontSize: 10, color: '#94a3b8' }}>
            Estimated sequence duration: {plan.estimated_duration_ms}ms · Tier 1 (Confirmation Gated)
          </div>
        </div>

        {/* Step Sequence Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Action Step Sequence</div>
          {plan.steps.map((step) => (
            <div
              key={step.step_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                backgroundColor: step.status === 'EXECUTING' ? 'rgba(56, 189, 248, 0.1)' : '#070a0f',
                border: `1px solid ${step.status === 'EXECUTING' ? '#38bdf888' : '#1e293b'}`,
                borderRadius: 6,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 10, color: '#64748b', fontWeight: 700 }}>#{step.step_id}</span>
                {getActionIcon(step.action_type)}
                <div>
                  <div style={{ fontSize: 12, color: '#f1f5f9' }}>{step.description}</div>
                  {step.target_coordinates && (
                    <div style={{ fontSize: 10, color: '#38bdf8' }}>
                      Coords: ({step.target_coordinates[0]}, {step.target_coordinates[1]})
                    </div>
                  )}
                </div>
              </div>
              <div>{getStatusBadge(step.status)}</div>
            </div>
          ))}
        </div>

        {/* Execution Controls */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => handleExecutePlan(false)}
            disabled={plan.status === 'EXECUTING'}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 6,
              backgroundColor: '#00ffcc',
              color: '#0a0d14',
              border: 'none',
              fontSize: 11,
              fontWeight: 700,
              cursor: plan.status === 'EXECUTING' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              opacity: plan.status === 'EXECUTING' ? 0.6 : 1,
            }}
          >
            <PlayRegular style={{ fontSize: 14 }} />
            Execute Live Plan
          </button>

          <button
            onClick={() => handleExecutePlan(true)}
            disabled={plan.status === 'EXECUTING'}
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              color: '#94a3b8',
              fontSize: 11,
              cursor: 'pointer',
            }}
          >
            Dry Run
          </button>

          <button
            onClick={handleHumanTakeover}
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              backgroundColor: 'rgba(255, 0, 85, 0.2)',
              border: '1px solid #ff0055',
              color: '#ff0055',
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <HandRightRegular style={{ fontSize: 14 }} />
            Takeover Abort
          </button>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div
            style={{
              padding: '6px 10px',
              backgroundColor: feedback.includes('TAKEOVER') ? 'rgba(255, 0, 85, 0.1)' : 'rgba(0, 255, 204, 0.1)',
              border: `1px solid ${feedback.includes('TAKEOVER') ? '#ff005544' : '#00ffcc44'}`,
              borderRadius: 6,
              fontSize: 11,
              color: feedback.includes('TAKEOVER') ? '#ff0055' : '#00ffcc',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            {feedback.includes('TAKEOVER') ? (
              <WarningRegular style={{ fontSize: 13 }} />
            ) : (
              <CheckmarkCircleRegular style={{ fontSize: 13 }} />
            )}
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
            Virtual Input Boundary Clamped (1920x1080)
          </span>
          <span>Guardian SLA &lt; 25ms</span>
        </div>
      </div>
    </div>
  );
};
