import React, { useState, useEffect } from 'react';
import {
  Button,
  Badge,
} from '@fluentui/react-components';
import {
  CheckmarkCircleRegular,
  DismissCircleRegular,
  Speaker2Regular,
  SendRegular,
  ClockRegular,
} from '@fluentui/react-icons';

export interface DualHandoffBriefing {
  dag_id: string;
  goal: string;
  spoken_summary: string;
  word_count: number;
  telegram_card_markdown: string;
  success: boolean;
  step_count: number;
  duration_s: number;
  screenshots_attached: number;
}

export interface WorkflowHandoffCardProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const WorkflowHandoffCard: React.FC<WorkflowHandoffCardProps> = ({
  externalEvent,
  onClose,
}) => {
  const [briefing, setBriefing] = useState<DualHandoffBriefing | null>(null);

  useEffect(() => {
    if (!externalEvent) return;
    const { type, payload } = externalEvent;

    if (type === 'WORKFLOW_HANDOFF_BRIEFING') {
      setBriefing(payload as DualHandoffBriefing);
    }
  }, [externalEvent]);

  if (!briefing) return null;

  const handleDismiss = () => {
    setBriefing(null);
    if (onClose) onClose();
  };

  return (
    <div
      style={{
        background: 'rgba(10, 15, 26, 0.95)',
        border: '1px solid rgba(0, 229, 255, 0.4)',
        borderRadius: 12,
        padding: '16px 20px',
        margin: '12px 0',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(16px)',
        color: '#f8fafc',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Speaker2Regular style={{ color: '#00e5ff', fontSize: 20 }} />
          <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: '0.04em', color: '#00e5ff' }}>
            DUAL HANDOFF DEBRIEF
          </span>
          <Badge
            appearance="filled"
            style={{
              background: briefing.success ? 'rgba(34, 197, 94, 0.25)' : 'rgba(239, 68, 68, 0.25)',
              color: briefing.success ? '#22c55e' : '#ef4444',
              fontWeight: 700,
            }}
          >
            {briefing.success ? 'COMPLETED' : 'PAUSED'}
          </Badge>
        </div>

        <button
          onClick={handleDismiss}
          style={{
            background: 'none',
            border: 'none',
            color: '#64748b',
            cursor: 'pointer',
            fontSize: 16,
            padding: 4,
          }}
          title="Dismiss Debrief"
        >
          <DismissCircleRegular />
        </button>
      </div>

      {/* Spoken Jarvis Briefing */}
      <div
        style={{
          background: 'rgba(0, 229, 255, 0.06)',
          borderLeft: '3px solid #00e5ff',
          borderRadius: 6,
          padding: '10px 14px',
          marginBottom: 12,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', letterSpacing: '0.05em' }}>
            SPOKEN JARVIS BRIEFING
          </span>
          <span style={{ fontSize: 10, color: '#94a3b8' }}>
            {briefing.word_count} words (&le; 25)
          </span>
        </div>
        <div style={{ fontSize: 13, fontStyle: 'italic', color: '#f1f5f9', lineHeight: 1.4 }}>
          &ldquo;{briefing.spoken_summary}&rdquo;
        </div>
      </div>

      {/* Telegram Companion Sync & Telemetry */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(0, 0, 0, 0.35)',
          borderRadius: 8,
          padding: '8px 12px',
          fontSize: 11,
          border: '1px solid rgba(255, 255, 255, 0.05)',
          marginBottom: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#38bdf8' }}>
          <SendRegular style={{ fontSize: 14 }} />
          <span>Telegram Companion Synced</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: '#94a3b8' }}>
          <span>{briefing.step_count} steps</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <ClockRegular style={{ fontSize: 12 }} />
            <span>{briefing.duration_s.toFixed(1)}s</span>
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          size="small"
          appearance="primary"
          icon={<CheckmarkCircleRegular />}
          onClick={handleDismiss}
          style={{
            background: '#0284c7',
            color: '#ffffff',
            fontWeight: 600,
          }}
        >
          Acknowledge
        </Button>
      </div>
    </div>
  );
};
