import React, { useState } from 'react';
import {
  Dialog,
  DialogSurface,
  DialogTitle,
  DialogBody,
  DialogActions,
  DialogContent,
  Button,
  Badge,
  Checkbox
} from '@fluentui/react-components';
import {
  ShieldRegular,
  ChevronDownRegular,
  ChevronUpRegular,
  CheckmarkRegular,
  DismissRegular
} from '@fluentui/react-icons';
import { ConfirmRequestPayload } from '../types/protocol';

interface ConfirmationModalProps {
  request: ConfirmRequestPayload | null;
  onRespond: (decision: 'approved' | 'denied', rememberChoice: boolean) => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({ request, onRespond }) => {
  const [remember, setRemember] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  if (!request) return null;

  const isTier1 = request.tier === 1;
  const isTier2 = request.tier === 2;
  const isTier3 = request.tier === 3;

  // Resolve target identifier
  const rawArgs = request.args || {};
  const target =
    rawArgs.target ||
    rawArgs.path ||
    rawArgs.dest ||
    rawArgs.src ||
    rawArgs.url ||
    rawArgs.app_name ||
    rawArgs.filename ||
    request.tool;

  // Resolve item count
  let itemCount = 1;
  if (Array.isArray(rawArgs.files)) itemCount = rawArgs.files.length;
  else if (Array.isArray(rawArgs.items)) itemCount = rawArgs.items.length;
  else if (Array.isArray(rawArgs.file_paths)) itemCount = rawArgs.file_paths.length;
  else if (typeof rawArgs.wordlist_size === 'number') itemCount = rawArgs.wordlist_size;

  // Fixed Tier Label (fixes F10 bug where everything non-Tier 2 rendered 'REVERSIBLE CHANGE')
  const getTierLabel = () => {
    if (isTier3) return 'TIER 3 • BLOCKED / SYSTEM RESTRICTED';
    if (isTier2) return 'TIER 2 • DESTRUCTIVE / EXTERNAL';
    if (isTier1) return 'TIER 1 • REVERSIBLE CHANGE';
    return `TIER ${request.tier} • READ-ONLY`;
  };

  const getTierColor = () => {
    if (isTier3) return '#ef4444';
    if (isTier2) return '#f97316';
    if (isTier1) return '#00e5ff';
    return '#34d399';
  };

  return (
    <Dialog open={true}>
      <DialogSurface
        style={{
          backgroundColor: '#080d1a',
          border: `1px solid ${isTier2 || isTier3 ? 'rgba(239, 68, 68, 0.5)' : 'rgba(0, 229, 255, 0.4)'}`,
          boxShadow: isTier2 || isTier3
            ? '0 20px 60px rgba(0, 0, 0, 0.9), 0 0 30px rgba(239, 68, 68, 0.35)'
            : '0 20px 60px rgba(0, 0, 0, 0.9), 0 0 30px rgba(0, 229, 255, 0.25)',
          borderRadius: 16,
          maxWidth: 620,
          padding: '20px 24px'
        }}
      >
        <DialogBody>
          <DialogTitle
            action={
              <Badge
                appearance="filled"
                size="medium"
                style={{
                  background: isTier2 || isTier3 ? 'rgba(239, 68, 68, 0.25)' : 'rgba(0, 229, 255, 0.2)',
                  color: getTierColor(),
                  border: `1px solid ${getTierColor()}`,
                  fontWeight: 700,
                  fontSize: 11,
                  letterSpacing: '0.4px'
                }}
              >
                {getTierLabel()}
              </Badge>
            }
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#f8fafc', fontSize: 16 }}>
              <ShieldRegular style={{ color: getTierColor(), fontSize: 20 }} />
              Security Confirmation Required
            </div>
          </DialogTitle>

          <DialogContent style={{ display: 'flex', flexDirection: 'column', gap: 12, paddingTop: 14 }}>
            {/* One-Line Summary Invariant: Tier, Target, Item Count (Task 6E.6) */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                borderRadius: 10,
                background: 'rgba(15, 23, 42, 0.85)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: '#f8fafc',
                fontSize: 13,
                fontFamily: 'Consolas, monospace',
                gap: 8
              }}
            >
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <span style={{ color: getTierColor(), fontWeight: 700 }}>[Tier {request.tier}]</span>{' '}
                <span style={{ color: '#f8fafc', fontWeight: 600 }}>{request.tool}</span> &bull;{' '}
                <span style={{ color: '#94a3b8' }}>Target:</span>{' '}
                <span style={{ color: '#ccff00' }}>{String(target)}</span>{' '}
                <span style={{ color: '#64748b' }}>({itemCount} item{itemCount !== 1 ? 's' : ''})</span>
              </div>
              <button
                onClick={() => setShowDetails(!showDetails)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  background: 'transparent',
                  border: 'none',
                  color: '#00e5ff',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: 600,
                  whiteSpace: 'nowrap'
                }}
              >
                <span>{showDetails ? 'Hide' : 'Details'}</span>
                {showDetails ? <ChevronUpRegular style={{ fontSize: 13 }} /> : <ChevronDownRegular style={{ fontSize: 13 }} />}
              </button>
            </div>

            {/* Expandable Details on Tap */}
            {showDetails && (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                  padding: 12,
                  borderRadius: 8,
                  background: 'rgba(4, 7, 13, 0.95)',
                  border: '1px solid rgba(0, 229, 255, 0.2)',
                  fontSize: 12,
                  color: '#cbd5e1'
                }}
              >
                <div>
                  <strong style={{ color: '#00e5ff' }}>Preview Description:</strong>
                  <div style={{ marginTop: 4, color: '#f1f5f9', lineHeight: 1.5 }}>{request.preview}</div>
                </div>
                {(request as any).folder && (
                  <div>
                    <strong style={{ color: '#94a3b8' }}>Target Scope Folder:</strong>
                    <div style={{ fontFamily: 'Consolas, monospace', color: '#ccff00', marginTop: 2 }}>{(request as any).folder}</div>
                  </div>
                )}
                <div>
                  <strong style={{ color: '#94a3b8' }}>Raw Parameters:</strong>
                  <pre
                    style={{
                      background: '#020408',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      padding: 8,
                      borderRadius: 6,
                      marginTop: 4,
                      color: '#94a3b8',
                      maxHeight: 120,
                      overflowY: 'auto',
                      fontSize: 11
                    }}
                  >
                    {JSON.stringify(rawArgs, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Remember Choice for Tier 1 Only */}
            {isTier1 && request.can_remember && (
              <Checkbox
                checked={remember}
                onChange={(_, data) => setRemember(Boolean(data.checked))}
                label="Approve and remember for this target folder (Tier 1 only)"
                style={{ color: '#94a3b8', fontSize: 12 }}
              />
            )}
          </DialogContent>

          <DialogActions style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, paddingTop: 16 }}>
            <Button
              appearance="secondary"
              icon={<DismissRegular />}
              style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#f87171',
                fontWeight: 600
              }}
              onClick={() => onRespond('denied', false)}
            >
              Deny
            </Button>
            <Button
              appearance="primary"
              icon={<CheckmarkRegular />}
              style={{
                background: isTier2
                  ? 'linear-gradient(135deg, #f97316, #ea580c)'
                  : 'linear-gradient(135deg, #00e5ff, #0052ff)',
                color: '#ffffff',
                fontWeight: 700,
                border: 'none',
                boxShadow: isTier2 ? '0 0 16px rgba(249, 115, 22, 0.4)' : '0 0 16px rgba(0, 229, 255, 0.4)'
              }}
              onClick={() => onRespond('approved', remember)}
            >
              Approve
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
};
