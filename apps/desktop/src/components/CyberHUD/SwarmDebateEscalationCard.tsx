import React, { useState } from 'react';
import {
  ShieldCheckmarkRegular,
  WarningRegular,
  CheckmarkCircleRegular,
  DismissRegular,
  ChevronDownRegular,
  ChevronUpRegular,
  BotRegular,
  CodeRegular,
} from '@fluentui/react-icons';
import { SwarmDebateEscalationPayload } from '../../types/protocol';

export interface SwarmDebateEscalationCardProps {
  escalation: SwarmDebateEscalationPayload;
  onDecision: (debateId: string, decision: 'approve' | 'reject', reason?: string) => void;
  onDismiss?: () => void;
}

export const SwarmDebateEscalationCard: React.FC<SwarmDebateEscalationCardProps> = ({
  escalation,
  onDecision,
  onDismiss,
}) => {
  const [expandedRole, setExpandedRole] = useState<string | null>(null);
  const [overrideReason, setOverrideReason] = useState<string>('');

  const {
    debate_id,
    proposal_title,
    proposal_description,
    risk_tier,
    final_score,
    verdict,
    gating_reasons,
    specialist_breakdown,
    last_turn_critiques,
  } = escalation;

  const scorePct = Math.round(final_score * 100);
  const isHighRisk = risk_tier >= 2;
  const isGatedPending = verdict === 'GATED_PENDING_UNANIMOUS';

  const specialists = [
    { key: 'security_auditor', label: 'Security Auditor', icon: ShieldCheckmarkRegular, color: '#FF3B30' },
    { key: 'lead_architect', label: 'Lead Architect', icon: BotRegular, color: '#00FFCC' },
    { key: 'qa_engineer', label: 'QA Engineer', icon: CheckmarkCircleRegular, color: '#0088FF' },
    { key: 'code_reviewer', label: 'Code Reviewer', icon: CodeRegular, color: '#FFB800' },
  ];

  const getVerdictBadge = (v?: string) => {
    switch (v) {
      case 'APPROVE':
        return { label: 'APPROVE', bg: 'rgba(0, 255, 204, 0.15)', border: '#00FFCC', color: '#00FFCC' };
      case 'BLOCK':
        return { label: 'BLOCK', bg: 'rgba(255, 59, 48, 0.2)', border: '#FF3B30', color: '#FF3B30' };
      case 'REQUEST_CHANGES':
      default:
        return { label: 'REQUEST CHANGES', bg: 'rgba(255, 184, 0, 0.2)', border: '#FFB800', color: '#FFB800' };
    }
  };

  const toggleRole = (key: string) => {
    setExpandedRole((prev) => (prev === key ? null : key));
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: '24px',
        right: '24px',
        width: '460px',
        maxHeight: '88vh',
        backgroundColor: 'rgba(10, 14, 23, 0.96)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        border: isHighRisk
          ? '1px solid rgba(255, 59, 48, 0.6)'
          : '1px solid rgba(255, 184, 0, 0.5)',
        boxShadow: isHighRisk
          ? '0 16px 48px rgba(0, 0, 0, 0.8), 0 0 24px rgba(255, 59, 48, 0.3)'
          : '0 16px 48px rgba(0, 0, 0, 0.8), 0 0 24px rgba(255, 184, 0, 0.25)',
        borderRadius: '16px',
        padding: '20px',
        color: '#E2E8F0',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        zIndex: 10000,
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        overflowY: 'auto',
      }}
    >
      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <WarningRegular style={{ color: isHighRisk ? '#FF3B30' : '#FFB800', fontSize: 20 }} />
          <span style={{ fontWeight: 600, fontSize: '15px', letterSpacing: '0.5px' }}>
            Swarm Synthetic Debate Escalation
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: isHighRisk ? 'rgba(255, 59, 48, 0.25)' : 'rgba(255, 184, 0, 0.2)',
              border: `1px solid ${isHighRisk ? '#FF3B30' : '#FFB800'}`,
              color: isHighRisk ? '#FF3B30' : '#FFB800',
            }}
          >
            TIER {risk_tier}
          </span>
          {onDismiss && (
            <button
              onClick={onDismiss}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94A3B8',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '4px',
              }}
            >
              <DismissRegular style={{ fontSize: 16 }} />
            </button>
          )}
        </div>
      </div>

      {/* Proposal Summary */}
      <div
        style={{
          backgroundColor: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '8px',
          padding: '12px',
        }}
      >
        <div style={{ fontWeight: 600, fontSize: '13px', color: '#F8FAFC', marginBottom: '4px' }}>
          {proposal_title}
        </div>
        <div style={{ fontSize: '12px', color: '#94A3B8', lineHeight: '1.4' }}>
          {proposal_description}
        </div>
      </div>

      {/* Consensus Score Gauge */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '12px' }}>
          <span style={{ color: '#94A3B8' }}>Consensus Score:</span>
          <span
            style={{
              fontWeight: 700,
              color: scorePct >= 85 ? '#00FFCC' : isHighRisk ? '#FF3B30' : '#FFB800',
            }}
          >
            {scorePct}% (Threshold: 85%)
          </span>
        </div>
        <div
          style={{
            height: '8px',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            borderRadius: '4px',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${Math.min(scorePct, 100)}%`,
              height: '100%',
              backgroundColor: scorePct >= 85 ? '#00FFCC' : isHighRisk ? '#FF3B30' : '#FFB800',
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      </div>

      {/* Gating Reasons */}
      {gating_reasons && gating_reasons.length > 0 && (
        <div
          style={{
            backgroundColor: 'rgba(255, 59, 48, 0.1)',
            border: '1px solid rgba(255, 59, 48, 0.3)',
            borderRadius: '6px',
            padding: '10px',
            fontSize: '11px',
            color: '#FF8080',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '4px' }}>
            {isGatedPending ? 'Unanimous Sign-Off Gate Pending:' : 'Escalation Triggers:'}
          </div>
          <ul style={{ margin: 0, paddingLeft: '16px' }}>
            {gating_reasons.map((reason, idx) => (
              <li key={idx} style={{ marginBottom: '2px' }}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Specialist Breakdown */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: '#94A3B8' }}>
          Specialist Stances:
        </div>
        {specialists.map(({ key, label, icon: Icon, color }) => {
          const critique = last_turn_critiques?.[key];
          const badge = getVerdictBadge(critique?.verdict);
          const isExpanded = expandedRole === key;
          const scoreVal = specialist_breakdown?.[key] !== undefined ? Math.round(specialist_breakdown[key] * 100) : null;

          return (
            <div
              key={key}
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                borderRadius: '8px',
                padding: '10px',
                cursor: 'pointer',
              }}
              onClick={() => toggleRole(key)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Icon style={{ color, fontSize: 16 }} />
                  <span style={{ fontSize: '12px', fontWeight: 600 }}>{label}</span>
                  {scoreVal !== null && (
                    <span style={{ fontSize: '10px', color: '#64748B' }}>({scoreVal}%)</span>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: badge.bg,
                      border: `1px solid ${badge.border}`,
                      color: badge.color,
                    }}
                  >
                    {badge.label}
                  </span>
                  {isExpanded ? <ChevronUpRegular style={{ fontSize: 14 }} /> : <ChevronDownRegular style={{ fontSize: 14 }} />}
                </div>
              </div>

              {/* Expanded details */}
              {isExpanded && critique && (
                <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.06)', fontSize: '11px', color: '#CBD5E1' }}>
                  {critique.concerns && critique.concerns.length > 0 && (
                    <div style={{ marginBottom: '6px' }}>
                      <strong style={{ color: '#FFB800' }}>Concerns:</strong>
                      <ul style={{ margin: '2px 0', paddingLeft: '16px' }}>
                        {critique.concerns.map((c: string, i: number) => <li key={i}>{c}</li>)}
                      </ul>
                    </div>
                  )}
                  {critique.recommendations && critique.recommendations.length > 0 && (
                    <div>
                      <strong style={{ color: '#00FFCC' }}>Recommendations:</strong>
                      <ul style={{ margin: '2px 0', paddingLeft: '16px' }}>
                        {critique.recommendations.map((r: string, i: number) => <li key={i}>{r}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Override Reason Input */}
      <div>
        <input
          type="text"
          placeholder="Optional justification or decision notes..."
          value={overrideReason}
          onChange={(e) => setOverrideReason(e.target.value)}
          style={{
            width: '100%',
            boxSizing: 'border-box',
            backgroundColor: 'rgba(0, 0, 0, 0.4)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '6px',
            padding: '8px 10px',
            color: '#F8FAFC',
            fontSize: '12px',
            outline: 'none',
          }}
        />
      </div>

      {/* Decision Buttons */}
      <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
        <button
          onClick={() => onDecision(debate_id, 'approve', overrideReason)}
          style={{
            flex: 1,
            backgroundColor: 'rgba(0, 255, 204, 0.2)',
            border: '1px solid #00FFCC',
            borderRadius: '8px',
            padding: '10px',
            color: '#00FFCC',
            fontWeight: 700,
            fontSize: '12px',
            cursor: 'pointer',
            transition: 'background-color 0.2s',
          }}
        >
          Override & Approve
        </button>
        <button
          onClick={() => onDecision(debate_id, 'reject', overrideReason)}
          style={{
            flex: 1,
            backgroundColor: 'rgba(255, 59, 48, 0.2)',
            border: '1px solid #FF3B30',
            borderRadius: '8px',
            padding: '10px',
            color: '#FF3B30',
            fontWeight: 700,
            fontSize: '12px',
            cursor: 'pointer',
            transition: 'background-color 0.2s',
          }}
        >
          Reject Proposal
        </button>
      </div>
    </div>
  );
};
