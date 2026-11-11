import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  GlobeRegular,
  PlayRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
  WarningRegular,
  BranchForkRegular,
  EyeRegular,
} from '@fluentui/react-icons';

export interface PlanBranchUI {
  branch_name: string;
  probability: number;
  final_verdict: string;
  accumulated_risk: number;
}

export interface CounterfactualReportUI {
  plan_title: string;
  nominal_feasibility_score: number;
  overall_safety_rating: string;
  branches: PlanBranchUI[];
  predicted_side_effects: string[];
  recommendations: string[];
}

interface WorldModelSimulatorHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const WorldModelSimulatorHUD: React.FC<WorldModelSimulatorHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [selectedPlanPreset, setSelectedPlanPreset] = useState<'safe' | 'risky'>('safe');
  const [report, setReport] = useState<CounterfactualReportUI>({
    plan_title: 'Feature Scaffold & Compilation Plan',
    nominal_feasibility_score: 0.90,
    overall_safety_rating: 'SAFE_TO_DISPATCH',
    branches: [
      {
        branch_name: 'NOMINAL_SUCCESS',
        probability: 0.85,
        final_verdict: 'PASS',
        accumulated_risk: 0.10,
      },
      {
        branch_name: 'COUNTERFACTUAL_PERMISSION_FALLBACK',
        probability: 0.10,
        final_verdict: 'RECOVERABLE_ERROR',
        accumulated_risk: 0.10,
      },
      {
        branch_name: 'COUNTERFACTUAL_TIMEOUT_INTERRUPT',
        probability: 0.05,
        final_verdict: 'RECOVERABLE_ERROR',
        accumulated_risk: 0.05,
      },
    ],
    predicted_side_effects: [
      "In-memory mutation of file 'services/backend/feature.py'",
      "Focus shift from 'Phenom Cyber Desktop' to 'Visual Studio Code'",
    ],
    recommendations: [
      'Nominal success confidence projected at 90%.',
      'Total forecasted collateral side-effects: 2.',
    ],
  });

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'simulation.update' && externalEvent.payload) {
      if (externalEvent.payload.report) setReport(externalEvent.payload.report);
    }
  }, [externalEvent]);

  const handleRunSimulation = (type: 'safe' | 'risky') => {
    setSelectedPlanPreset(type);
    if (type === 'safe') {
      setReport({
        plan_title: 'Feature Scaffold & Compilation Plan',
        nominal_feasibility_score: 0.90,
        overall_safety_rating: 'SAFE_TO_DISPATCH',
        branches: [
          {
            branch_name: 'NOMINAL_SUCCESS',
            probability: 0.85,
            final_verdict: 'PASS',
            accumulated_risk: 0.10,
          },
          {
            branch_name: 'COUNTERFACTUAL_PERMISSION_FALLBACK',
            probability: 0.10,
            final_verdict: 'RECOVERABLE_ERROR',
            accumulated_risk: 0.10,
          },
          {
            branch_name: 'COUNTERFACTUAL_TIMEOUT_INTERRUPT',
            probability: 0.05,
            final_verdict: 'RECOVERABLE_ERROR',
            accumulated_risk: 0.05,
          },
        ],
        predicted_side_effects: [
          "In-memory mutation of file 'services/backend/feature.py'",
          "Focus shift from 'Phenom Cyber Desktop' to 'Visual Studio Code'",
        ],
        recommendations: [
          'Nominal success confidence projected at 90%.',
          'Total forecasted collateral side-effects: 2.',
        ],
      });
      setFeedback('Simulated Safe Plan: 90% Feasibility, 0 High-Risk Anomalies.');
    } else {
      setReport({
        plan_title: 'Emergency Cache Purge & Process Restart',
        nominal_feasibility_score: 0.55,
        overall_safety_rating: 'REQUIRES_CONFIRMATION',
        branches: [
          {
            branch_name: 'NOMINAL_SUCCESS',
            probability: 0.48,
            final_verdict: 'PASS',
            accumulated_risk: 0.45,
          },
          {
            branch_name: 'COUNTERFACTUAL_PERMISSION_FALLBACK',
            probability: 0.35,
            final_verdict: 'RECOVERABLE_ERROR',
            accumulated_risk: 0.30,
          },
          {
            branch_name: 'COUNTERFACTUAL_TIMEOUT_INTERRUPT',
            probability: 0.17,
            final_verdict: 'FATAL_BLOCKED',
            accumulated_risk: 0.25,
          },
        ],
        predicted_side_effects: [
          "Simulated soft-delete (recycle bin) of file 'cache/temp_store.db'",
          'Simulated termination of process PID 1002 (electron.exe)',
          'High risk destructive command pattern detected: rm -rf tmp/',
        ],
        recommendations: [
          'Nominal success confidence projected at 55%.',
          'Total forecasted collateral side-effects: 3.',
          'Verify Tier 1 confirmations for potentially mutating steps.',
        ],
      });
      setFeedback('Simulated Risky Plan: 55% Feasibility, Tier 1 Confirmation Required.');
    }

    if (sendMessage) {
      sendMessage({
        type: 'simulation.run',
        payload: { preset: type },
      });
    }

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
          <GlobeRegular style={{ color: '#00f0ff', fontSize: 20 }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, letterSpacing: 0.5 }}>
              CONTEXTUAL WORLD-MODEL SIMULATOR
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 26-03 • Counterfactual Plan Projection • Side-Effect Forecasting
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
        {/* Preset Plan Simulator Buttons */}
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => handleRunSimulation('safe')}
            style={{
              flex: 1,
              padding: '8px 14px',
              backgroundColor: selectedPlanPreset === 'safe' ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255, 255, 255, 0.04)',
              border: selectedPlanPreset === 'safe' ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 6,
              color: '#fff',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            <PlayRegular style={{ fontSize: 14, color: '#38bdf8' }} />
            Simulate Safe Plan
          </button>
          <button
            onClick={() => handleRunSimulation('risky')}
            style={{
              flex: 1,
              padding: '8px 14px',
              backgroundColor: selectedPlanPreset === 'risky' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(255, 255, 255, 0.04)',
              border: selectedPlanPreset === 'risky' ? '1px solid #f59e0b' : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 6,
              color: '#fff',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            <WarningRegular style={{ fontSize: 14, color: '#f59e0b' }} />
            Simulate Mutating Plan
          </button>
        </div>

        {/* Plan Feasibility & Safety Card */}
        <div
          style={{
            padding: 14,
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid rgba(0, 240, 255, 0.2)',
            borderRadius: 8,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#f8fafc' }}>{report.plan_title}</div>
            <span
              style={{
                fontSize: 11,
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: 12,
                backgroundColor:
                  report.overall_safety_rating === 'SAFE_TO_DISPATCH'
                    ? 'rgba(16, 185, 129, 0.2)'
                    : 'rgba(245, 158, 11, 0.2)',
                color: report.overall_safety_rating === 'SAFE_TO_DISPATCH' ? '#34d399' : '#fbbf24',
                border:
                  report.overall_safety_rating === 'SAFE_TO_DISPATCH'
                    ? '1px solid rgba(16, 185, 129, 0.4)'
                    : '1px solid rgba(245, 158, 11, 0.4)',
              }}
            >
              {report.overall_safety_rating}
            </span>
          </div>

          {/* Feasibility Meter */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>
              <span>Nominal Feasibility Confidence</span>
              <span style={{ fontWeight: 600, color: '#00f0ff' }}>{(report.nominal_feasibility_score * 100).toFixed(0)}%</span>
            </div>
            <div style={{ height: 8, backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: 4, overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${report.nominal_feasibility_score * 100}%`,
                  backgroundColor:
                    report.nominal_feasibility_score >= 0.8
                      ? '#10b981'
                      : report.nominal_feasibility_score >= 0.5
                      ? '#f59e0b'
                      : '#ef4444',
                  boxShadow: '0 0 10px rgba(0, 240, 255, 0.5)',
                  transition: 'width 0.4s ease',
                }}
              />
            </div>
          </div>
        </div>

        {/* Counterfactual Branches */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#38bdf8', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <BranchForkRegular style={{ fontSize: 14 }} />
            COUNTERFACTUAL OUTCOME BRANCHES ({report.branches.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {report.branches.map((b, idx) => (
              <div
                key={idx}
                style={{
                  padding: '10px 14px',
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 6,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#f1f5f9' }}>{b.branch_name}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                    Probability: {(b.probability * 100).toFixed(0)}% • Verdict: {b.final_verdict}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: b.accumulated_risk > 0.25 ? '#ef4444' : '#10b981',
                    }}
                  >
                    Risk: {(b.accumulated_risk * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Forecasted Collateral Side-Effects */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#f59e0b', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <EyeRegular style={{ fontSize: 14 }} />
            FORECASTED COLLATERAL SIDE-EFFECTS ({report.predicted_side_effects.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {report.predicted_side_effects.map((effect, idx) => (
              <div
                key={idx}
                style={{
                  padding: '8px 12px',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: 6,
                  fontSize: 11,
                  color: '#cbd5e1',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <div style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#f59e0b' }} />
                <span>{effect}</span>
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
          Virtual In-Memory Sandbox • Non-Destructive (Rule 7)
        </span>
        <span>Guardian SLA &lt; 25ms Active</span>
      </div>
    </div>
  );
};
