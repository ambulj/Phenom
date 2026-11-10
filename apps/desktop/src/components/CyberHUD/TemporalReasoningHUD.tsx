import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  BrainCircuitRegular,
  ClockRegular,
  ArrowClockwiseRegular,
  CheckmarkCircleRegular,
  WarningRegular,
} from '@fluentui/react-icons';

export interface TemporalPreferenceHUD {
  intent_id: string;
  category: string;
  statement: string;
  valid_from_str: string;
  is_active: boolean;
  superseded_by?: string;
  confidence: number;
}

export interface DecisionAlternativeHUD {
  name: string;
  description: string;
  score: number;
  pros: string[];
  cons: string[];
  rejected_reason: string;
}

export interface DecisionExplanationHUD {
  decision_id: string;
  objective: string;
  chosen_plan: string;
  rationale: string;
  alternatives: DecisionAlternativeHUD[];
  citations: string[];
  confidence: number;
}

interface TemporalReasoningHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const TemporalReasoningHUD: React.FC<TemporalReasoningHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'decision' | 'lineage' | 'conflicts'>('decision');
  const [newCategory, setNewCategory] = useState<string>('coding_style');
  const [newStatement, setNewStatement] = useState<string>('');

  const [preferences, setPreferences] = useState<TemporalPreferenceHUD[]>([
    {
      intent_id: 'intent_01a',
      category: 'coding_style',
      statement: 'Prefer atomic worktree sandboxes with local pytest verification',
      valid_from_str: '2026-11-10 14:20',
      is_active: true,
      confidence: 0.98,
    },
    {
      intent_id: 'intent_02b',
      category: 'privacy',
      statement: 'Zero cloud audio egress: keep all Whisper & TTS streams strictly in RAM buffers',
      valid_from_str: '2026-11-09 09:15',
      is_active: true,
      confidence: 1.0,
    },
    {
      intent_id: 'intent_00x',
      category: 'coding_style',
      statement: 'Direct in-place edits on primary branch (Legacy)',
      valid_from_str: '2026-11-01 10:00',
      is_active: false,
      superseded_by: 'intent_01a',
      confidence: 0.85,
    },
  ]);

  const [explanation] = useState<DecisionExplanationHUD>({
    decision_id: 'dec_88f12a',
    objective: 'Orchestrate distributed refactor of billing system with local safety guarantees',
    chosen_plan: 'Topological Swarm DAG (Wave Partitioning)',
    rationale:
      'Topological wave execution groups mutually independent AST analysis and research tasks into concurrent subagents, reducing latency by 68% while guaranteeing isolated worktree safety.',
    alternatives: [
      {
        name: 'Single-Threaded Sequential Runner',
        description: 'Execute research, AST mapping, coding, and tests strictly one after another in primary workspace',
        score: 0.42,
        pros: ['Minimal orchestration memory overhead', 'Simple synchronous logging'],
        cons: ['3.4x slower execution latency', 'No sandbox isolation on test regressions'],
        rejected_reason: 'Fails execution speed target and risks dirtying primary worktree',
      },
      {
        name: 'Cloud-Delegated Swarm Cluster',
        description: 'Dispatch parallel tasks to remote serverless worker pool',
        score: 0.18,
        pros: ['High scalable burst throughput'],
        cons: ['Violates Rule 4 (Zero Cloud Exfiltration)', 'Network dependency penalty'],
        rejected_reason: 'Strictly prohibited by permanent Safety Rule 4 (100% Offline Local Autonomy)',
      },
    ],
    citations: [
      '[1] SAFETY.md: Rule 1 (Safety Before Tools)',
      '[2] SAFETY.md: Rule 4 (Zero Cloud Exfiltration)',
      '[3] User Intent: intent_01a (Atomic Worktree Sandboxes)',
    ],
    confidence: 0.96,
  });

  useEffect(() => {
    if (externalEvent?.type === 'reasoning.explanation_update' && externalEvent.payload) {
      // Handle live explanation updates
    }
  }, [externalEvent]);

  const handleRecordPreference = () => {
    if (!newStatement.trim()) return;
    const newPref: TemporalPreferenceHUD = {
      intent_id: `intent_${Date.now().toString(16).slice(-6)}`,
      category: newCategory,
      statement: newStatement.trim(),
      valid_from_str: 'Just now',
      is_active: true,
      confidence: 0.95,
    };
    setPreferences((prev) => [newPref, ...prev]);
    setNewStatement('');

    if (sendMessage) {
      sendMessage({
        type: 'memory.record_preference',
        payload: { category: newCategory, statement: newStatement.trim() },
      });
    }
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(10, 15, 26, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(16, 185, 129, 0.35)',
        borderRadius: 12,
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.7), 0 0 25px rgba(16, 185, 129, 0.18)',
        display: 'flex',
        flexDirection: 'column',
        color: '#e2e8f0',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          borderBottom: '1px solid rgba(16, 185, 129, 0.2)',
          background: 'rgba(6, 78, 59, 0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <BrainCircuitRegular style={{ fontSize: 22, color: '#10b981' }} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: 0.5, color: '#34d399' }}>
              TEMPORAL INTENT MEMORY & COUNTERFACTUAL REASONING ENGINE
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 22-02 • Historical Lineage Graph & Counterfactual Decision Explainer
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ display: 'flex', background: 'rgba(255, 255, 255, 0.05)', borderRadius: 6, padding: 2 }}>
            <button
              onClick={() => setActiveTab('decision')}
              style={{
                background: activeTab === 'decision' ? 'rgba(16, 185, 129, 0.25)' : 'transparent',
                color: activeTab === 'decision' ? '#34d399' : '#94a3b8',
                border: 'none',
                padding: '4px 12px',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              Decision Rationale
            </button>
            <button
              onClick={() => setActiveTab('lineage')}
              style={{
                background: activeTab === 'lineage' ? 'rgba(16, 185, 129, 0.25)' : 'transparent',
                color: activeTab === 'lineage' ? '#34d399' : '#94a3b8',
                border: 'none',
                padding: '4px 12px',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              Temporal Lineage
            </button>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: 4,
                display: 'flex',
              }}
            >
              <DismissRegular style={{ fontSize: 18 }} />
            </button>
          )}
        </div>
      </div>

      {/* Main Body */}
      <div style={{ flex: 1, padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {activeTab === 'decision' ? (
          <>
            {/* Objective & Chosen Plan */}
            <div
              style={{
                padding: 16,
                borderRadius: 8,
                background: 'rgba(16, 185, 129, 0.06)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
              }}
            >
              <div style={{ fontSize: 11, color: '#6ee7b7', textTransform: 'uppercase', fontWeight: 600 }}>
                Chosen Execution Plan
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#ecfdf5', marginTop: 4 }}>
                {explanation.chosen_plan}
              </div>
              <div style={{ fontSize: 13, color: '#cbd5e1', marginTop: 6, lineHeight: 1.5 }}>
                {explanation.rationale}
              </div>

              {/* Citations */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
                {explanation.citations.map((c, i) => (
                  <span
                    key={i}
                    style={{
                      fontSize: 11,
                      fontFamily: 'monospace',
                      background: 'rgba(16, 185, 129, 0.15)',
                      color: '#a7f3d0',
                      padding: '3px 8px',
                      borderRadius: 4,
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                    }}
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>

            {/* Counterfactual Alternatives Table */}
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 8, textTransform: 'uppercase' }}>
                Counterfactual Candidate Alternatives (Why Not?)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {explanation.alternatives.map((alt, i) => (
                  <div
                    key={i}
                    style={{
                      padding: 14,
                      borderRadius: 8,
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: '#f87171' }}>{alt.name}</span>
                      <span style={{ fontSize: 12, color: '#ef4444', fontFamily: 'monospace' }}>
                        Score: {(alt.score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>{alt.description}</div>

                    <div style={{ marginTop: 8, fontSize: 12, color: '#fca5a5', display: 'flex', gap: 6, alignItems: 'center' }}>
                      <WarningRegular style={{ fontSize: 14 }} />
                      <span><strong>Rejected Reason:</strong> {alt.rejected_reason}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <>
            {/* Quick Add Preference */}
            <div
              style={{
                display: 'flex',
                gap: 10,
                padding: 12,
                borderRadius: 8,
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.07)',
              }}
            >
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                style={{
                  background: '#0f172a',
                  color: '#e2e8f0',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: 6,
                  padding: '6px 10px',
                  fontSize: 12,
                }}
              >
                <option value="coding_style">Coding Style</option>
                <option value="privacy">Privacy & Security</option>
                <option value="toolchain">Toolchain & Models</option>
                <option value="voice">Voice & Persona</option>
              </select>

              <input
                type="text"
                placeholder="Record or refine temporal preference directive..."
                value={newStatement}
                onChange={(e) => setNewStatement(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRecordPreference()}
                style={{
                  flex: 1,
                  background: '#0f172a',
                  color: '#e2e8f0',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: 6,
                  padding: '6px 12px',
                  fontSize: 13,
                }}
              />

              <button
                onClick={handleRecordPreference}
                style={{
                  background: 'linear-gradient(135deg, #059669, #10b981)',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: 6,
                  padding: '6px 16px',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Record
              </button>
            </div>

            {/* Preference Timeline List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {preferences.map((p) => (
                <div
                  key={p.intent_id}
                  style={{
                    padding: 12,
                    borderRadius: 8,
                    background: p.is_active ? 'rgba(16, 185, 129, 0.05)' : 'rgba(255, 255, 255, 0.015)',
                    border: p.is_active
                      ? '1px solid rgba(16, 185, 129, 0.3)'
                      : '1px solid rgba(255, 255, 255, 0.05)',
                    opacity: p.is_active ? 1 : 0.6,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          background: p.is_active ? 'rgba(16, 185, 129, 0.2)' : 'rgba(148, 163, 184, 0.15)',
                          color: p.is_active ? '#34d399' : '#94a3b8',
                          padding: '2px 6px',
                          borderRadius: 4,
                        }}
                      >
                        {p.category}
                      </span>
                      <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#64748b' }}>
                        {p.intent_id}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94a3b8' }}>
                      <ClockRegular style={{ fontSize: 13 }} />
                      <span>{p.valid_from_str}</span>
                      {p.is_active ? (
                        <CheckmarkCircleRegular style={{ color: '#10b981', fontSize: 14 }} />
                      ) : (
                        <ArrowClockwiseRegular style={{ color: '#eab308', fontSize: 14 }} />
                      )}
                    </div>
                  </div>

                  <div style={{ fontSize: 13, color: p.is_active ? '#f1f5f9' : '#94a3b8', marginTop: 6 }}>
                    {p.statement}
                  </div>

                  {p.superseded_by && (
                    <div style={{ fontSize: 11, color: '#eab308', marginTop: 4 }}>
                      Superseded by <code style={{ color: '#fde047' }}>{p.superseded_by}</code>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Footer Status Bar */}
      <div
        style={{
          padding: '8px 20px',
          background: 'rgba(0, 0, 0, 0.3)',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 11,
          color: '#64748b',
        }}
      >
        <div style={{ display: 'flex', gap: 12 }}>
          <span>Preferences: {preferences.filter((p) => p.is_active).length} active</span>
          <span>Lineage Depth: {preferences.length} records</span>
        </div>
        <div>Rule 4 Offline Local • Rule 7 Non-Destructive Memory</div>
      </div>
    </div>
  );
};
