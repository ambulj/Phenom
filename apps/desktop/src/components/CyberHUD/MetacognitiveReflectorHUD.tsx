import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  BrainCircuitRegular,
  DocumentSparkleRegular,
  SparkleRegular,
  GaugeRegular,
  ArrowClockwiseRegular,
  CheckmarkCircleRegular,
} from '@fluentui/react-icons';

export interface TrajectoryAuditHUD {
  audit_id: string;
  user_intent: string;
  steps_count: number;
  successful_steps: number;
  failed_steps: number;
  epistemic_confidence: number;
  calibration_score: number;
  root_cause_analysis?: string;
  suggested_prompt_mitigation?: string;
}

interface MetacognitiveReflectorHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const MetacognitiveReflectorHUD: React.FC<MetacognitiveReflectorHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [calibrationScore, setCalibrationScore] = useState<number>(0.96);
  const [averageConfidence, setAverageConfidence] = useState<number>(0.92);
  const [totalAudits, setTotalAudits] = useState<number>(14);

  const [recentAudits, setRecentAudits] = useState<TrajectoryAuditHUD[]>([
    {
      audit_id: 'audit_7a9f21',
      user_intent: 'Decompose and execute billing refactor across topological subagent DAG',
      steps_count: 5,
      successful_steps: 5,
      failed_steps: 0,
      epistemic_confidence: 0.94,
      calibration_score: 0.98,
      root_cause_analysis: 'All 5 wave steps executed within nominal latency SLA without regressions.',
      suggested_prompt_mitigation: 'Maintain current subagent wave grouping and Kahn topological heuristics.',
    },
    {
      audit_id: 'audit_3c81e0',
      user_intent: 'Choreograph dual-monitor windows into research reading preset',
      steps_count: 3,
      successful_steps: 3,
      failed_steps: 0,
      epistemic_confidence: 0.90,
      calibration_score: 0.95,
      root_cause_analysis: 'Window coordinate mapping successfully scaled to 4K primary and FHD portrait secondary.',
      suggested_prompt_mitigation: 'Pre-warm display topology detection cache on active window switch.',
    },
  ]);

  const [activeAudit, setActiveAudit] = useState<TrajectoryAuditHUD>(recentAudits[0]);
  const [loggedStatus, setLoggedStatus] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'metacognition.audit_update' && externalEvent.payload) {
      if (externalEvent.payload.average_calibration_score !== undefined) {
        setCalibrationScore(externalEvent.payload.average_calibration_score);
      }
      if (externalEvent.payload.average_confidence !== undefined) {
        setAverageConfidence(externalEvent.payload.average_confidence);
      }
      if (externalEvent.payload.total_audits !== undefined) {
        setTotalAudits(externalEvent.payload.total_audits);
      }
      if (externalEvent.payload.recent_audits) {
        setRecentAudits(externalEvent.payload.recent_audits);
        setActiveAudit(externalEvent.payload.recent_audits[0]);
      }
    }
  }, [externalEvent]);

  const handleLogNote = () => {
    if (!activeAudit) return;
    setLoggedStatus(`Saved to .phenom/reflection/REFLECTION_${activeAudit.audit_id}.md`);
    if (sendMessage) {
      sendMessage({
        type: 'metacognition.record_reflection_note',
        payload: { audit_id: activeAudit.audit_id },
      });
    }
    setTimeout(() => setLoggedStatus(null), 3000);
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(10, 15, 26, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(168, 85, 247, 0.35)',
        borderRadius: 12,
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.7), 0 0 25px rgba(168, 85, 247, 0.18)',
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
          borderBottom: '1px solid rgba(168, 85, 247, 0.2)',
          background: 'rgba(126, 34, 206, 0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <BrainCircuitRegular style={{ fontSize: 22, color: '#c084fc' }} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: 0.5, color: '#d8b4fe' }}>
              METACOGNITIVE REFLECTOR & CALIBRATION ENGINE
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 23-01 • Post-Execution Trajectory Auditing & Epistemic Uncertainty (META-01 / COG-01)
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={handleLogNote}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'rgba(168, 85, 247, 0.2)',
              color: '#d8b4fe',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              borderRadius: 6,
              padding: '4px 10px',
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            <DocumentSparkleRegular style={{ fontSize: 14 }} />
            <span>Save to Reflection Vault</span>
          </button>

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

      {/* Main Content */}
      <div style={{ flex: 1, padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Metacognitive Metrics Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          <div
            style={{
              padding: 14,
              borderRadius: 8,
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(168, 85, 247, 0.25)',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}
          >
            <GaugeRegular style={{ fontSize: 24, color: '#c084fc' }} />
            <div>
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>Calibration Accuracy</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#f3e8ff', marginTop: 2 }}>
                {(calibrationScore * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          <div
            style={{
              padding: 14,
              borderRadius: 8,
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}
          >
            <SparkleRegular style={{ fontSize: 24, color: '#38bdf8' }} />
            <div>
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>Epistemic Confidence</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#bae6fd', marginTop: 2 }}>
                {(averageConfidence * 100).toFixed(0)}% Mean
              </div>
            </div>
          </div>

          <div
            style={{
              padding: 14,
              borderRadius: 8,
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}
          >
            <ArrowClockwiseRegular style={{ fontSize: 24, color: '#34d399' }} />
            <div>
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>Audited Trajectories</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#a7f3d0', marginTop: 2 }}>
                {totalAudits} Cycles
              </div>
            </div>
          </div>
        </div>

        {/* Selected Trajectory Post-Mortem View */}
        {activeAudit && (
          <div
            style={{
              padding: 16,
              borderRadius: 8,
              background: 'rgba(168, 85, 247, 0.06)',
              border: '1px solid rgba(168, 85, 247, 0.25)',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: '#d8b4fe', textTransform: 'uppercase' }}>
                Trajectory Audit: {activeAudit.audit_id}
              </span>
              <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#c084fc' }}>
                Calibration: {(activeAudit.calibration_score * 100).toFixed(0)}%
              </span>
            </div>

            <div style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 600 }}>
              &ldquo;{activeAudit.user_intent}&rdquo;
            </div>

            {/* Root Cause Banner */}
            <div
              style={{
                marginTop: 6,
                padding: 10,
                borderRadius: 6,
                background: 'rgba(0, 0, 0, 0.3)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                fontSize: 12,
                color: '#cbd5e1',
              }}
            >
              <div style={{ color: '#94a3b8', fontSize: 11, textTransform: 'uppercase', marginBottom: 2 }}>Root Cause Analysis</div>
              {activeAudit.root_cause_analysis}
            </div>

            {/* Suggested Mitigation Banner */}
            <div
              style={{
                padding: 10,
                borderRadius: 6,
                background: 'rgba(56, 189, 248, 0.08)',
                border: '1px solid rgba(56, 189, 248, 0.2)',
                fontSize: 12,
                color: '#7dd3fc',
              }}
            >
              <div style={{ color: '#38bdf8', fontSize: 11, textTransform: 'uppercase', marginBottom: 2 }}>Prompt &amp; Planning Mitigation</div>
              {activeAudit.suggested_prompt_mitigation}
            </div>
          </div>
        )}

        {/* Status Toast */}
        {loggedStatus && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              background: 'rgba(52, 211, 153, 0.15)',
              border: '1px solid rgba(52, 211, 153, 0.3)',
              color: '#34d399',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <CheckmarkCircleRegular style={{ fontSize: 14 }} />
            <span>{loggedStatus}</span>
          </div>
        )}
      </div>

      {/* Footer */}
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
        <div>Reflective Vault: .phenom/reflection/ • Rule 4 100% Offline Local Model</div>
        <div>Guardian SLA &lt; 25.0ms • Self-Correcting Metacognition</div>
      </div>
    </div>
  );
};
