import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  BrainCircuitRegular,
  ArrowSyncRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
  WarningRegular,
  HistoryRegular,
  LightbulbRegular,
} from '@fluentui/react-icons';

export interface EpistemicBeliefUI {
  belief_id: string;
  subject: string;
  predicate: string;
  object_value: string;
  confidence: number;
  prior_confidence: number;
  evidence_count: number;
  source: string;
  is_active: boolean;
  updated_at: number;
}

export interface BeliefRevisionUI {
  revision_id: string;
  belief_id: string;
  old_value: string;
  new_value: string;
  confidence_delta: number;
  reason: string;
  timestamp: number;
}

interface EpistemicBeliefNetworkHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const EpistemicBeliefNetworkHUD: React.FC<EpistemicBeliefNetworkHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [beliefs, setBeliefs] = useState<EpistemicBeliefUI[]>([
    {
      belief_id: 'bel_001',
      subject: 'User',
      predicate: 'prefers_theme',
      object_value: 'Dark Cyberpunk Glow',
      confidence: 0.95,
      prior_confidence: 0.50,
      evidence_count: 5,
      source: 'USER_STATEMENT',
      is_active: true,
      updated_at: Date.now() - 3600000,
    },
    {
      belief_id: 'bel_002',
      subject: 'Backend',
      predicate: 'uses_framework',
      object_value: 'FastAPI + WebSocket',
      confidence: 0.99,
      prior_confidence: 0.80,
      evidence_count: 12,
      source: 'DEFAULT_ASSUMPTION',
      is_active: true,
      updated_at: Date.now() - 7200000,
    },
    {
      belief_id: 'bel_003',
      subject: 'Safety',
      predicate: 'enforces_kill_switch_sla',
      object_value: '< 25.0ms Universal Halt',
      confidence: 1.0,
      prior_confidence: 1.0,
      evidence_count: 100,
      source: 'DEFAULT_ASSUMPTION',
      is_active: true,
      updated_at: Date.now() - 14400000,
    },
  ]);

  const [revisions, setRevisions] = useState<BeliefRevisionUI[]>([
    {
      revision_id: 'rev_001',
      belief_id: 'bel_001',
      old_value: 'Light Theme',
      new_value: 'Dark Cyberpunk Glow',
      confidence_delta: 0.45,
      reason: 'Direct user instruction',
      timestamp: Date.now() - 3600000,
    },
  ]);

  // Contradiction Test & Resolution Form
  const [testSubj, setTestSubj] = useState<string>('User');
  const [testPred, setTestPred] = useState<string>('prefers_theme');
  const [testValue, setTestValue] = useState<string>('Light Solar Glow');
  const [isDirectUser, setIsDirectUser] = useState<boolean>(true);
  const [analysisResult, setAnalysisResult] = useState<{
    conflict: boolean;
    strategy: string;
    explanation: string;
  } | null>(null);

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'epistemic.update' && externalEvent.payload) {
      if (externalEvent.payload.beliefs) setBeliefs(externalEvent.payload.beliefs);
      if (externalEvent.payload.revisions) setRevisions(externalEvent.payload.revisions);
    }
  }, [externalEvent]);

  const handleAnalyzeClaim = () => {
    const key = `${testSubj}::${testPred}`.toLowerCase();
    const existing = beliefs.find((b) => `${b.subject}::${b.predicate}`.toLowerCase() === key);

    if (!existing) {
      setAnalysisResult({
        conflict: false,
        strategy: 'NO_CONFLICT',
        explanation: `No prior belief exists for [${testSubj}] ${testPred}. Safe to assert as new proposition.`,
      });
      return;
    }

    if (existing.object_value.toLowerCase() === testValue.toLowerCase()) {
      setAnalysisResult({
        conflict: false,
        strategy: 'NO_CONFLICT',
        explanation: `Claim matches existing belief value '${existing.object_value}'. Reinforces Bayesian confidence.`,
      });
      return;
    }

    // Contradiction detected
    if (isDirectUser) {
      setAnalysisResult({
        conflict: true,
        strategy: 'OVERWRITE_WITH_USER_CORRECTION',
        explanation: `Contradiction detected: Current belief is '${existing.object_value}' (conf: ${existing.confidence}). Direct user authority supersedes prior belief.`,
      });
    } else {
      setAnalysisResult({
        conflict: true,
        strategy: 'CONFIDENCE_DEGRADATION',
        explanation: `Contradiction from indirect source: Existing belief '${existing.object_value}' degraded by -0.25 pending confirmation.`,
      });
    }
  };

  const handleApplyResolution = () => {
    const key = `${testSubj}::${testPred}`.toLowerCase();
    const existingIdx = beliefs.findIndex((b) => `${b.subject}::${b.predicate}`.toLowerCase() === key);

    if (existingIdx >= 0) {
      const existing = beliefs[existingIdx];
      const oldVal = existing.object_value;
      const oldConf = existing.confidence;
      const newConf = isDirectUser ? 0.95 : Math.max(0.20, oldConf - 0.25);
      const delta = +(newConf - oldConf).toFixed(2);

      const updatedBeliefs = [...beliefs];
      updatedBeliefs[existingIdx] = {
        ...existing,
        object_value: isDirectUser ? testValue : existing.object_value,
        prior_confidence: oldConf,
        confidence: newConf,
        evidence_count: existing.evidence_count + 1,
        source: isDirectUser ? 'USER_STATEMENT' : 'INFERRED',
        updated_at: Date.now(),
      };
      setBeliefs(updatedBeliefs);

      const newRev: BeliefRevisionUI = {
        revision_id: `rev_${Date.now()}`,
        belief_id: existing.belief_id,
        old_value: oldVal,
        new_value: isDirectUser ? testValue : `${oldVal} (Degraded)`,
        confidence_delta: delta,
        reason: analysisResult?.explanation || 'Applied resolution',
        timestamp: Date.now(),
      };
      setRevisions([newRev, ...revisions]);
    } else {
      const newBelief: EpistemicBeliefUI = {
        belief_id: `bel_${Date.now()}`,
        subject: testSubj,
        predicate: testPred,
        object_value: testValue,
        confidence: 0.85,
        prior_confidence: 0.50,
        evidence_count: 1,
        source: isDirectUser ? 'USER_STATEMENT' : 'INFERRED',
        is_active: true,
        updated_at: Date.now(),
      };
      setBeliefs([...beliefs, newBelief]);
    }

    if (sendMessage) {
      sendMessage({
        type: 'epistemic.apply_resolution',
        payload: {
          subject: testSubj,
          predicate: testPred,
          value: testValue,
          is_user_direct: isDirectUser,
        },
      });
    }

    setFeedback(`Resolved & applied proposition [${testSubj}] ${testPred} -> '${testValue}'`);
    setAnalysisResult(null);
    setTimeout(() => setFeedback(null), 3000);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 40,
        right: 40,
        width: 660,
        maxHeight: 'calc(100vh - 80px)',
        backgroundColor: 'rgba(10, 18, 28, 0.96)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 240, 255, 0.35)',
        borderRadius: 12,
        boxShadow: '0 8px 32px rgba(0, 240, 255, 0.15)',
        color: '#e2e8f0',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        fontFamily: 'Segoe UI, -apple-system, sans-serif',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(0, 240, 255, 0.05)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <BrainCircuitRegular style={{ color: '#00f0ff', fontSize: 20 }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, letterSpacing: 0.5 }}>
              EPISTEMIC BELIEF NETWORK & CONTRADICTION RESOLVER
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 26-02 • Bayesian Proposition Weights • Rational Conflict Resolution
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: 4,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <DismissRegular style={{ fontSize: 18 }} />
        </button>
      </div>

      {feedback && (
        <div
          style={{
            padding: '8px 18px',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            borderBottom: '1px solid rgba(16, 185, 129, 0.3)',
            color: '#34d399',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <CheckmarkCircleRegular style={{ fontSize: 16 }} />
          <span>{feedback}</span>
        </div>
      )}

      {/* Content scroll area */}
      <div style={{ padding: 18, overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Active Propositions Matrix */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#00f0ff', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <LightbulbRegular style={{ fontSize: 14 }} />
            ACTIVE BELIEF PROPOSITIONS ({beliefs.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {beliefs.map((b) => (
              <div
                key={b.belief_id}
                style={{
                  padding: '10px 14px',
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(0, 240, 255, 0.15)',
                  borderRadius: 8,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>
                    <span style={{ color: '#38bdf8' }}>[{b.subject}]</span> {b.predicate}:{' '}
                    <span style={{ color: '#a78bfa' }}>"{b.object_value}"</span>
                  </div>
                  <span
                    style={{
                      fontSize: 10,
                      padding: '2px 8px',
                      borderRadius: 10,
                      backgroundColor: b.source === 'USER_STATEMENT' ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255, 255, 255, 0.08)',
                      color: b.source === 'USER_STATEMENT' ? '#38bdf8' : '#94a3b8',
                      border: b.source === 'USER_STATEMENT' ? '1px solid rgba(0, 240, 255, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)',
                    }}
                  >
                    {b.source}
                  </span>
                </div>

                {/* Confidence Bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ fontSize: 11, color: '#94a3b8', width: 110 }}>
                    Confidence: {(b.confidence * 100).toFixed(0)}%
                  </div>
                  <div style={{ flex: 1, height: 6, backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: 3, overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.min(100, b.confidence * 100)}%`,
                        backgroundColor: b.confidence >= 0.9 ? '#10b981' : b.confidence >= 0.6 ? '#f59e0b' : '#ef4444',
                        boxShadow: '0 0 8px rgba(0, 240, 255, 0.5)',
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                  <div style={{ fontSize: 10, color: '#64748b' }}>
                    Ev: {b.evidence_count}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Contradiction Evaluator & Resolver */}
        <div
          style={{
            padding: 14,
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: 8,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 600, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 6 }}>
            <ArrowSyncRegular style={{ fontSize: 14 }} />
            CONTRADICTION DETECTOR & RESOLVER
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.5fr', gap: 8 }}>
            <div>
              <label style={{ fontSize: 10, color: '#94a3b8' }}>Subject</label>
              <input
                type="text"
                value={testSubj}
                onChange={(e) => setTestSubj(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: 2,
                  padding: '6px 8px',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: 4,
                  color: '#fff',
                  fontSize: 12,
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: 10, color: '#94a3b8' }}>Predicate</label>
              <input
                type="text"
                value={testPred}
                onChange={(e) => setTestPred(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: 2,
                  padding: '6px 8px',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: 4,
                  color: '#fff',
                  fontSize: 12,
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: 10, color: '#94a3b8' }}>Claimed Value</label>
              <input
                type="text"
                value={testValue}
                onChange={(e) => setTestValue(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: 2,
                  padding: '6px 8px',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: 4,
                  color: '#fff',
                  fontSize: 12,
                }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={isDirectUser}
                onChange={(e) => setIsDirectUser(e.target.checked)}
              />
              <span>Direct User Statement (Authoritative Override)</span>
            </label>

            <button
              onClick={handleAnalyzeClaim}
              style={{
                padding: '6px 14px',
                backgroundColor: 'rgba(0, 240, 255, 0.15)',
                border: '1px solid rgba(0, 240, 255, 0.4)',
                borderRadius: 4,
                color: '#00f0ff',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Analyze Contradiction
            </button>
          </div>

          {analysisResult && (
            <div
              style={{
                marginTop: 6,
                padding: 10,
                backgroundColor: analysisResult.conflict ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                border: analysisResult.conflict ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: 6,
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span
                  style={{
                    fontWeight: 600,
                    fontSize: 12,
                    color: analysisResult.conflict ? '#f87171' : '#34d399',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  {analysisResult.conflict ? <WarningRegular style={{ fontSize: 16 }} /> : <CheckmarkCircleRegular style={{ fontSize: 16 }} />}
                  Strategy: {analysisResult.strategy}
                </span>
                <button
                  onClick={handleApplyResolution}
                  style={{
                    padding: '4px 12px',
                    backgroundColor: '#00f0ff',
                    border: 'none',
                    borderRadius: 4,
                    color: '#000',
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Apply Resolution
                </button>
              </div>
              <div style={{ fontSize: 11, color: '#cbd5e1' }}>{analysisResult.explanation}</div>
            </div>
          )}
        </div>

        {/* Revision Delta History */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#f59e0b', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <HistoryRegular style={{ fontSize: 14 }} />
            REVISION AUDIT LOG ({revisions.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {revisions.map((r) => (
              <div
                key={r.revision_id}
                style={{
                  padding: '8px 12px',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 6,
                  fontSize: 11,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ color: '#e2e8f0' }}>
                    <span style={{ textDecoration: 'line-through', color: '#94a3b8' }}>"{r.old_value}"</span> →{' '}
                    <span style={{ color: '#38bdf8', fontWeight: 600 }}>"{r.new_value}"</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>{r.reason}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span
                    style={{
                      color: r.confidence_delta >= 0 ? '#10b981' : '#ef4444',
                      fontWeight: 600,
                    }}
                  >
                    {r.confidence_delta >= 0 ? `+${r.confidence_delta}` : `${r.confidence_delta}`}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '10px 18px',
          borderTop: '1px solid rgba(0, 240, 255, 0.2)',
          fontSize: 11,
          color: '#64748b',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(0, 240, 255, 0.02)',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShieldCheckmarkRegular style={{ color: '#00f0ff' }} />
          Rule 1 & Rule 8 Invariants Strictly Enforced
        </span>
        <span>Bayesian Updating Active</span>
      </div>
    </div>
  );
};
