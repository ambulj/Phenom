import React, { useState, useEffect } from 'react';
import {
  BranchRegular,
  CheckmarkCircleRegular,
  DismissRegular,
  ChevronDownRegular,
  ChevronUpRegular,
  SparkleRegular,
} from '@fluentui/react-icons';
import { MissionMorningDebriefPayload } from '../../types/protocol';

export interface MorningDebriefCardProps {
  debrief: MissionMorningDebriefPayload;
  onReviewBranch?: (branchName: string, worktreePath: string) => void;
  onMergeChanges?: (branchName: string) => void;
  onDismiss?: () => void;
}

export const MorningDebriefCard: React.FC<MorningDebriefCardProps> = ({
  debrief,
  onReviewBranch,
  onMergeChanges,
  onDismiss,
}) => {
  const [expandedMissionId, setExpandedMissionId] = useState<string | null>(null);

  // Trigger Three.js particle orb visual celebration on mount
  useEffect(() => {
    if (debrief.celebrate || debrief.summary.successful_missions > 0) {
      window.dispatchEvent(
        new CustomEvent('phenom:orb:celebrate', {
          detail: {
            tests_fixed: debrief.summary.tests_fixed,
            type: 'morning_debrief',
          },
        })
      );
    }
  }, [debrief]);

  const { summary } = debrief;
  const hasSuccessful = summary.successful_missions > 0;

  const toggleExpand = (mid: string) => {
    setExpandedMissionId((prev) => (prev === mid ? null : mid));
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: '24px',
        right: '24px',
        width: '440px',
        maxHeight: '85vh',
        backgroundColor: 'rgba(8, 12, 20, 0.94)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: hasSuccessful
          ? '1px solid rgba(0, 255, 204, 0.4)'
          : '1px solid rgba(0, 82, 255, 0.35)',
        boxShadow: hasSuccessful
          ? '0 12px 40px 0 rgba(0, 0, 0, 0.7), 0 0 20px 0 rgba(0, 255, 204, 0.25)'
          : '0 8px 32px 0 rgba(0, 0, 0, 0.6), 0 0 16px 0 rgba(0, 82, 255, 0.2)',
        borderRadius: '14px',
        padding: '18px',
        color: '#E2E8F0',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
        overflow: 'hidden',
      }}
    >
      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <SparkleRegular style={{ color: '#00FFCC', fontSize: 18 }} />
          <span
            style={{
              fontSize: '11px',
              fontFamily: 'monospace',
              fontWeight: 700,
              letterSpacing: '1px',
              textTransform: 'uppercase',
              color: '#00FFCC',
            }}
          >
            🌙 Overnight Sovereign Debrief
          </span>
        </div>
        <button
          onClick={onDismiss}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#64748B',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            borderRadius: '4px',
          }}
          title="Dismiss debrief"
        >
          <DismissRegular style={{ fontSize: 16 }} />
        </button>
      </div>

      {/* Aggregated KPI Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          background: 'rgba(15, 23, 42, 0.65)',
          padding: '10px',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.06)',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>
            Missions
          </div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#38BDF8' }}>
            {summary.successful_missions} / {summary.total_missions}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>
            Tests Healed
          </div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#CCFF00' }}>
            +{summary.tests_fixed}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>
            Diff Stat
          </div>
          <div style={{ fontSize: '13px', fontWeight: 600, fontFamily: 'monospace', marginTop: '2px' }}>
            <span style={{ color: '#4ADE80' }}>+{summary.lines_added}</span>{' '}
            <span style={{ color: '#F87171' }}>-{summary.lines_deleted}</span>
          </div>
        </div>
      </div>

      {/* Executive Briefing Text */}
      <div
        style={{
          fontSize: '12px',
          lineHeight: '1.5',
          color: '#CBD5E1',
          background: 'rgba(0, 82, 255, 0.08)',
          borderLeft: '3px solid #0052FF',
          padding: '8px 12px',
          borderRadius: '0 6px 6px 0',
          fontStyle: 'italic',
        }}
      >
        "{summary.executive_summary}"
      </div>

      {/* Individual Missions List */}
      <div
        style={{
          maxHeight: '260px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          paddingRight: '4px',
        }}
      >
        {summary.missions.map((m) => {
          const isExpanded = expandedMissionId === m.mission_id;
          const isSuccess = m.status === 'completed';
          const statusColor = isSuccess ? '#4ADE80' : m.status === 'healing' ? '#FACC15' : '#F87171';

          return (
            <div
              key={m.mission_id}
              style={{
                background: 'rgba(30, 41, 59, 0.5)',
                border: `1px solid ${isSuccess ? 'rgba(74, 222, 128, 0.25)' : 'rgba(248, 113, 113, 0.25)'}`,
                borderRadius: '8px',
                padding: '10px',
                fontSize: '12px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  cursor: 'pointer',
                }}
                onClick={() => toggleExpand(m.mission_id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0 }}>
                  {isSuccess ? (
                    <CheckmarkCircleRegular style={{ color: '#4ADE80', fontSize: 16 }} />
                  ) : (
                    <DismissRegular style={{ color: '#F87171', fontSize: 16 }} />
                  )}
                  <span
                    style={{
                      fontWeight: 600,
                      color: '#F1F5F9',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {m.title}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span
                    style={{
                      fontSize: '10px',
                      textTransform: 'uppercase',
                      color: statusColor,
                      fontFamily: 'monospace',
                      fontWeight: 700,
                    }}
                  >
                    {m.status}
                  </span>
                  {isExpanded ? (
                    <ChevronUpRegular style={{ fontSize: 14, color: '#94A3B8' }} />
                  ) : (
                    <ChevronDownRegular style={{ fontSize: 14, color: '#94A3B8' }} />
                  )}
                </div>
              </div>

              {/* Collapsible Details */}
              {isExpanded && (
                <div
                  style={{
                    marginTop: '10px',
                    paddingTop: '8px',
                    borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    fontSize: '11px',
                    color: '#94A3B8',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <BranchRegular style={{ fontSize: 14, color: '#38BDF8' }} />
                    <span style={{ fontFamily: 'monospace', color: '#38BDF8' }}>{m.branch_name}</span>
                  </div>
                  <div>
                    Fixed Tests: <strong style={{ color: '#CCFF00' }}>{m.tests_fixed}</strong> | Lines:{' '}
                    <span style={{ color: '#4ADE80' }}>+{m.lines_added}</span> /{' '}
                    <span style={{ color: '#F87171' }}>-{m.lines_deleted}</span>
                  </div>
                  {m.files_changed && m.files_changed.length > 0 && (
                    <div>
                      Files:{' '}
                      <span style={{ fontFamily: 'monospace', color: '#E2E8F0' }}>
                        {m.files_changed.join(', ')}
                      </span>
                    </div>
                  )}
                  {m.diagnostic_log && (
                    <div
                      style={{
                        background: 'rgba(0, 0, 0, 0.4)',
                        padding: '6px',
                        borderRadius: '4px',
                        fontFamily: 'monospace',
                        fontSize: '10px',
                        maxHeight: '70px',
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap',
                        color: '#CBD5E1',
                      }}
                    >
                      {m.diagnostic_log}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onReviewBranch?.(m.branch_name, m.worktree_path);
                      }}
                      style={{
                        background: 'rgba(0, 82, 255, 0.25)',
                        border: '1px solid #0052FF',
                        color: '#60A5FA',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        cursor: 'pointer',
                      }}
                    >
                      Review Branch
                    </button>
                    {isSuccess && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onMergeChanges?.(m.branch_name);
                        }}
                        style={{
                          background: 'rgba(74, 222, 128, 0.2)',
                          border: '1px solid #4ADE80',
                          color: '#4ADE80',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          cursor: 'pointer',
                        }}
                      >
                        Merge Changes
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom Footer Actions */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
        <button
          onClick={onDismiss}
          style={{
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            color: '#CBD5E1',
            padding: '6px 14px',
            borderRadius: '6px',
            fontSize: '12px',
            cursor: 'pointer',
          }}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
};
