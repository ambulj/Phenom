import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  BrainCircuitRegular,
  CheckmarkCircleRegular,
  FlashRegular,
  LightbulbRegular,
} from '@fluentui/react-icons';

export interface AnticipatedActionItem {
  action_id: string;
  target_action: string;
  source_action?: string;
  probability: number;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  reason: string;
  prewarmed?: boolean;
}

export interface CacheEntryItem {
  target_name: string;
  target_type: string;
  status: string;
  size_kb: number;
  hit_count: number;
}

interface PredictiveTaskHubHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const PredictiveTaskHubHUD: React.FC<PredictiveTaskHubHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [currentAction, setCurrentAction] = useState<string>('git_commit');
  const [anticipatedActions, setAnticipatedActions] = useState<AnticipatedActionItem[]>([
    {
      action_id: 'ant_git_commit_git_push',
      target_action: 'git_push --set-upstream origin',
      source_action: 'git_commit',
      probability: 0.82,
      confidence_level: 'HIGH',
      reason: 'P(git_push | git_commit) = 82.0% across 28 sequential observations.',
      prewarmed: true,
    },
    {
      action_id: 'ant_git_commit_run_tests',
      target_action: 'pytest services/backend/tests -v',
      source_action: 'git_commit',
      probability: 0.64,
      confidence_level: 'MEDIUM',
      reason: 'P(run_tests | git_commit) = 64.0% in test-driven habit cycles.',
      prewarmed: true,
    },
    {
      action_id: 'ant_git_commit_deploy_preview',
      target_action: 'npm run build:preview',
      source_action: 'git_commit',
      probability: 0.45,
      confidence_level: 'LOW',
      reason: 'P(deploy_preview | git_commit) = 45.0% conditional pipeline.',
      prewarmed: false,
    },
  ]);

  const [cacheEntries, setCacheEntries] = useState<CacheEntryItem[]>([
    {
      target_name: 'services.backend.synapse.ast_symbols',
      target_type: 'ast_symbols',
      status: 'WARM',
      size_kb: 42,
      hit_count: 14,
    },
    {
      target_name: 'git_push.credentials.token_ref',
      target_type: 'credential_ref',
      status: 'WARM',
      size_kb: 8,
      hit_count: 22,
    },
    {
      target_name: 'pytest.test_metacognitive_reflection',
      target_type: 'test_ast',
      status: 'WARM',
      size_kb: 64,
      hit_count: 9,
    },
  ]);

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'predictive.anticipation_update' && externalEvent.payload) {
      if (externalEvent.payload.current_action) setCurrentAction(externalEvent.payload.current_action);
      if (externalEvent.payload.predictions) setAnticipatedActions(externalEvent.payload.predictions);
    }
  }, [externalEvent]);

  const handleSimulateAction = (actionName: string) => {
    setCurrentAction(actionName);
    setFeedback(`Active habit node switched to: ${actionName}`);

    if (actionName === 'edit_code') {
      setAnticipatedActions([
        {
          action_id: 'ant_edit_code_run_tests',
          target_action: 'pytest services/backend/tests -v',
          source_action: 'edit_code',
          probability: 0.88,
          confidence_level: 'HIGH',
          reason: 'P(run_tests | edit_code) = 88.0% based on post-edit habit loop.',
          prewarmed: true,
        },
        {
          action_id: 'ant_edit_code_git_diff',
          target_action: 'git diff --stat',
          source_action: 'edit_code',
          probability: 0.72,
          confidence_level: 'HIGH',
          reason: 'P(git_diff | edit_code) = 72.0% change-tracking frequency.',
          prewarmed: true,
        },
      ]);
    } else if (actionName === 'open_repo') {
      setAnticipatedActions([
        {
          action_id: 'ant_open_repo_git_pull',
          target_action: 'git pull --rebase',
          source_action: 'open_repo',
          probability: 0.91,
          confidence_level: 'HIGH',
          reason: 'P(git_pull | open_repo) = 91.0% startup synchronization.',
          prewarmed: true,
        },
        {
          action_id: 'ant_open_repo_git_status',
          target_action: 'git status',
          source_action: 'open_repo',
          probability: 0.85,
          confidence_level: 'HIGH',
          reason: 'P(git_status | open_repo) = 85.0% working-tree baseline check.',
          prewarmed: true,
        },
      ]);
    } else {
      setAnticipatedActions([
        {
          action_id: 'ant_git_commit_git_push',
          target_action: 'git_push --set-upstream origin',
          source_action: 'git_commit',
          probability: 0.82,
          confidence_level: 'HIGH',
          reason: 'P(git_push | git_commit) = 82.0% across 28 sequential observations.',
          prewarmed: true,
        },
      ]);
    }

    if (sendMessage) {
      sendMessage({
        type: 'predictive.simulate_action',
        payload: { action: actionName },
      });
    }
  };

  const handleDismissCard = (actionId: string) => {
    setAnticipatedActions((prev) => prev.filter((item) => item.action_id !== actionId));
    setFeedback(`Soft-dismissed card '${actionId}' (Rule 7 non-destructibility).`);
    if (sendMessage) {
      sendMessage({
        type: 'predictive.dismiss_card',
        payload: { action_id: actionId },
      });
    }
  };

  const handlePrewarmTarget = (targetName: string) => {
    setFeedback(`Pre-warming cache target: ${targetName}...`);
    const newEntry: CacheEntryItem = {
      target_name: targetName,
      target_type: 'workflow_context',
      status: 'WARM',
      size_kb: 24,
      hit_count: 1,
    };
    setCacheEntries((prev) => [newEntry, ...prev]);
    if (sendMessage) {
      sendMessage({
        type: 'predictive.prewarm_target',
        payload: { target_name: targetName },
      });
    }
  };

  return (
    <div
      style={{
        width: '780px',
        maxHeight: '85vh',
        background: 'rgba(12, 16, 28, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(0, 240, 255, 0.35)',
        borderRadius: '14px',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 240, 255, 0.2)',
        color: '#E0E6ED',
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        zIndex: 1000,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 20px',
          borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
          background: 'linear-gradient(90deg, rgba(0, 240, 255, 0.08), rgba(120, 80, 255, 0.04))',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <BrainCircuitRegular style={{ fontSize: '24px', color: '#00F0FF' }} />
          <div>
            <div
              style={{
                fontSize: '15px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                color: '#FFFFFF',
                textTransform: 'uppercase',
              }}
            >
              PREDICTIVE TASK ANTICIPATION & AMBIENT PIPELINING
            </div>
            <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.55)' }}>
              Markov Transition Chain Model & Background Cache Pre-Warmer (AUT-04)
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#8A99AD',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <DismissRegular style={{ fontSize: '18px' }} />
        </button>
      </div>

      {/* Main Body */}
      <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Habit State Context */}
        <div
          style={{
            background: 'rgba(18, 24, 38, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <div style={{ fontSize: '11px', color: '#00F0FF', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              CURRENT DETECTED HABIT STATE
            </div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: '#00F0FF' }}>●</span> {currentAction}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            {['git_commit', 'edit_code', 'open_repo'].map((action) => (
              <button
                key={action}
                onClick={() => handleSimulateAction(action)}
                style={{
                  background: currentAction === action ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                  border: `1px solid ${currentAction === action ? '#00F0FF' : 'rgba(255, 255, 255, 0.15)'}`,
                  color: currentAction === action ? '#00F0FF' : '#E0E6ED',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  transition: 'all 0.2s',
                }}
              >
                {action}
              </button>
            ))}
          </div>
        </div>

        {/* Anticipated Action Cards */}
        <div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#A0B2C6', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <LightbulbRegular style={{ color: '#00F0FF' }} /> TOP ANTICIPATED WORKFLOW ACTIONS (P ≥ 0.40)
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {anticipatedActions.map((item) => (
              <div
                key={item.action_id}
                style={{
                  background: 'rgba(20, 28, 46, 0.75)',
                  border: '1px solid rgba(0, 240, 255, 0.2)',
                  borderRadius: '10px',
                  padding: '14px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span
                      style={{
                        background:
                          item.confidence_level === 'HIGH'
                            ? 'rgba(0, 255, 136, 0.15)'
                            : item.confidence_level === 'MEDIUM'
                            ? 'rgba(0, 240, 255, 0.15)'
                            : 'rgba(255, 200, 0, 0.15)',
                        color:
                          item.confidence_level === 'HIGH'
                            ? '#00FF88'
                            : item.confidence_level === 'MEDIUM'
                            ? '#00F0FF'
                            : '#FFC800',
                        fontSize: '10px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        border: `1px solid ${
                          item.confidence_level === 'HIGH'
                            ? 'rgba(0, 255, 136, 0.3)'
                            : item.confidence_level === 'MEDIUM'
                            ? 'rgba(0, 240, 255, 0.3)'
                            : 'rgba(255, 200, 0, 0.3)'
                        }`,
                      }}
                    >
                      {item.confidence_level} CONFIDENCE ({(item.probability * 100).toFixed(0)}%)
                    </span>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF' }}>{item.target_action}</span>
                  </div>

                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                      onClick={() => handlePrewarmTarget(item.target_action)}
                      style={{
                        background: 'rgba(0, 240, 255, 0.1)',
                        border: '1px solid rgba(0, 240, 255, 0.3)',
                        color: '#00F0FF',
                        borderRadius: '6px',
                        padding: '4px 10px',
                        fontSize: '11px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <FlashRegular /> Pre-Warm
                    </button>
                    <button
                      onClick={() => handleDismissCard(item.action_id)}
                      style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.15)',
                        color: '#8A99AD',
                        borderRadius: '6px',
                        padding: '4px 8px',
                        fontSize: '11px',
                        cursor: 'pointer',
                      }}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>

                {/* Probability Bar */}
                <div style={{ width: '100%', height: '4px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${item.probability * 100}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #00F0FF, #00FF88)',
                      borderRadius: '2px',
                    }}
                  />
                </div>

                <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.55)' }}>{item.reason}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Cache Prewarmer Telemetry */}
        <div
          style={{
            background: 'rgba(18, 24, 38, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '16px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#A0B2C6', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <FlashRegular style={{ color: '#00FF88' }} /> BACKGROUND CACHE PRE-WARMER TELEMETRY (AUT-04)
            </div>
            <span style={{ fontSize: '11px', color: '#00FF88', fontWeight: 600 }}>● 64MB BUDGET ACTIVE</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '14px' }}>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ fontSize: '10px', color: '#8A99AD' }}>WARMED TARGETS</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>{cacheEntries.length}</div>
            </div>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ fontSize: '10px', color: '#8A99AD' }}>MEMORY FOOTPRINT</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#00F0FF', marginTop: '2px' }}>
                {cacheEntries.reduce((acc, c) => acc + c.size_kb, 0)} KB
              </div>
            </div>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ fontSize: '10px', color: '#8A99AD' }}>CACHE HITS</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#00FF88', marginTop: '2px' }}>
                {cacheEntries.reduce((acc, c) => acc + c.hit_count, 0)}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {cacheEntries.slice(0, 3).map((entry, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '11px',
                  padding: '6px 10px',
                  background: 'rgba(0, 0, 0, 0.25)',
                  borderRadius: '6px',
                  fontFamily: 'monospace',
                }}
              >
                <span style={{ color: '#E0E6ED' }}>{entry.target_name}</span>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <span style={{ color: '#00FF88' }}>{entry.status}</span>
                  <span style={{ color: '#8A99AD' }}>{entry.size_kb} KB</span>
                  <span style={{ color: '#00F0FF' }}>{entry.hit_count} hits</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Feedback alert */}
        {feedback && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              background: 'rgba(0, 240, 255, 0.1)',
              border: '1px solid rgba(0, 240, 255, 0.3)',
              fontSize: '11px',
              color: '#00F0FF',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <CheckmarkCircleRegular /> {feedback}
          </div>
        )}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '12px 20px',
          borderTop: '1px solid rgba(0, 240, 255, 0.15)',
          background: 'rgba(8, 12, 20, 0.6)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '11px',
          color: '#8A99AD',
        }}
      >
        <span>Rule 7 Non-Destructive Dismissal | Rule 8 Payment Defense Active</span>
        <button
          onClick={onClose}
          style={{
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            color: '#FFFFFF',
            borderRadius: '6px',
            padding: '6px 14px',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          Close HUD
        </button>
      </div>
    </div>
  );
};
