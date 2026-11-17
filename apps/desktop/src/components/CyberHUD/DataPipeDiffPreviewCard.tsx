import React, { useState, useEffect } from 'react';
import {
  Button,
  Badge,
} from '@fluentui/react-components';
import {
  CheckmarkCircleRegular,
  DismissCircleRegular,
  ShieldRegular,
} from '@fluentui/react-icons';

export interface DiffPreviewPayload {
  diff_id: string;
  target_file_path: string;
  existing_content: string;
  proposed_content: string;
  unified_diff: string;
  taint_source: string;
  status: 'pending' | 'approved' | 'rejected' | 'committed';
}

export interface DataPipeDiffPreviewCardProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const DataPipeDiffPreviewCard: React.FC<DataPipeDiffPreviewCardProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [diff, setDiff] = useState<DiffPreviewPayload | null>(null);

  useEffect(() => {
    if (!externalEvent) return;
    const { type, payload } = externalEvent;

    if (type === 'WORKFLOW_DIFF_PREVIEW_REQUESTED') {
      setDiff(payload as DiffPreviewPayload);
    } else if (type === 'WORKFLOW_DIFF_COMMITTED') {
      if (diff && diff.diff_id === payload.diff_id) {
        setDiff({ ...diff, status: 'committed' });
      }
    }
  }, [externalEvent]);

  if (!diff) return null;

  const handleApprove = () => {
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'commit_enclave_data_to_file',
          args: { diff_id: diff.diff_id },
        },
      });
    }
    setDiff((prev) => prev ? { ...prev, status: 'committed' } : null);
  };

  const handleReject = () => {
    setDiff(null);
    if (onClose) onClose();
  };

  const diffLines = diff.unified_diff.split('\n');

  return (
    <div
      style={{
        background: 'rgba(10, 13, 22, 0.96)',
        border: '1px solid rgba(245, 158, 11, 0.45)',
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
          <ShieldRegular style={{ color: '#f59e0b', fontSize: 20 }} />
          <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: '0.04em', color: '#f59e0b' }}>
            ENCLAVE DATA PIPE DIFF
          </span>
          <Badge
            appearance="filled"
            style={{
              background: 'rgba(239, 68, 68, 0.25)',
              color: '#ef4444',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              fontWeight: 700,
              fontSize: 11,
            }}
          >
            [UNTRUSTED_TAINT]
          </Badge>
          <Badge
            appearance="tint"
            style={{
              background: diff.status === 'committed' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)',
              color: diff.status === 'committed' ? '#22c55e' : '#f59e0b',
            }}
          >
            {diff.status.toUpperCase()}
          </Badge>
        </div>

        <button
          onClick={handleReject}
          style={{
            background: 'none',
            border: 'none',
            color: '#64748b',
            cursor: 'pointer',
            fontSize: 16,
            padding: 4,
          }}
          title="Dismiss Diff Preview"
        >
          <DismissCircleRegular />
        </button>
      </div>

      {/* Origin & File Metadata */}
      <div
        style={{
          background: 'rgba(0, 0, 0, 0.35)',
          borderRadius: 8,
          padding: '8px 12px',
          marginBottom: 12,
          fontSize: 12,
          border: '1px solid rgba(255, 255, 255, 0.05)',
        }}
      >
        <div style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
          <span style={{ color: '#94a3b8' }}>Target:</span>
          <span style={{ color: '#38bdf8', fontFamily: 'Consolas, monospace', fontWeight: 600 }}>
            {diff.target_file_path}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <span style={{ color: '#94a3b8' }}>Origin:</span>
          <span style={{ color: '#cbd5e1', wordBreak: 'break-all' }}>
            {diff.taint_source}
          </span>
        </div>
      </div>

      {/* Unified / Side-by-side Diff Viewer */}
      <div
        style={{
          maxHeight: 220,
          overflowY: 'auto',
          background: '#030712',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 6,
          padding: '8px 12px',
          fontFamily: 'Consolas, monospace',
          fontSize: 11,
          lineHeight: '1.45',
          marginBottom: 14,
        }}
      >
        {diffLines.map((line, idx) => {
          let bg = 'transparent';
          let color = '#94a3b8';
          if (line.startsWith('+') && !line.startsWith('+++')) {
            bg = 'rgba(34, 197, 94, 0.15)';
            color = '#4ade80';
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            bg = 'rgba(239, 68, 68, 0.15)';
            color = '#f87171';
          } else if (line.startsWith('@@')) {
            color = '#38bdf8';
            bg = 'rgba(56, 189, 248, 0.08)';
          }

          return (
            <div
              key={idx}
              style={{
                background: bg,
                color,
                padding: '1px 4px',
                borderRadius: 2,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {line || ' '}
            </div>
          );
        })}
      </div>

      {/* Action Controls */}
      {diff.status === 'pending' && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <Button
            size="small"
            appearance="subtle"
            icon={<DismissCircleRegular />}
            onClick={handleReject}
            style={{ color: '#94a3b8' }}
          >
            Discard
          </Button>
          <Button
            size="small"
            appearance="primary"
            icon={<CheckmarkCircleRegular />}
            onClick={handleApprove}
            style={{
              background: '#0284c7',
              color: '#ffffff',
              fontWeight: 600,
            }}
          >
            Authorize & Commit Diff
          </Button>
        </div>
      )}

      {diff.status === 'committed' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#4ade80', fontSize: 12 }}>
          <CheckmarkCircleRegular style={{ fontSize: 16 }} />
          <span>Committed to workspace with Rule 7 recycle backup.</span>
        </div>
      )}
    </div>
  );
};
