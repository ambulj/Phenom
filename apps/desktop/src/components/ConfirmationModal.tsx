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
import { WarningFilled } from '@fluentui/react-icons';
import { ConfirmRequestPayload } from '../types/protocol';

interface ConfirmationModalProps {
  request: ConfirmRequestPayload | null;
  onRespond: (decision: 'approved' | 'denied', rememberChoice: boolean) => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({ request, onRespond }) => {
  const [remember, setRemember] = useState(false);

  if (!request) return null;

  const isTier2 = request.tier === 2;
  const isTier3 = request.tier === 3;

  return (
    <Dialog open={true}>
      <DialogSurface style={{ backgroundColor: '#0f172a', border: '1px solid rgba(255, 255, 255, 0.15)' }}>
        <DialogBody>
          <DialogTitle
            action={
              <Badge
                appearance="filled"
                color={isTier3 ? 'danger' : isTier2 ? 'severe' : 'warning'}
                size="medium"
              >
                TIER {request.tier} {isTier2 ? 'DESTRUCTIVE / EXTERNAL' : 'REVERSIBLE CHANGE'}
              </Badge>
            }
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <WarningFilled style={{ color: isTier2 ? '#ef4444' : '#f59e0b' }} />
              Security Confirmation Required
            </div>
          </DialogTitle>

          <DialogContent style={{ display: 'flex', flexDirection: 'column', gap: 14, paddingTop: 12 }}>
            <div style={{ fontSize: 13, color: '#94a3b8' }}>
              Action requested: <strong style={{ color: '#f1f5f9' }}>{request.tool}</strong>
            </div>

            {/* Human Readable Preview */}
            <div
              style={{
                background: 'rgba(30, 41, 59, 0.7)',
                padding: '12px 16px',
                borderRadius: 8,
                border: '1px solid rgba(255, 255, 255, 0.08)',
                fontSize: 14,
                color: '#f8fafc',
                lineHeight: 1.5
              }}
            >
              {request.preview}
            </div>

            {/* Arguments */}
            <details style={{ fontSize: 12, color: '#64748b', cursor: 'pointer' }}>
              <summary>View raw parameters</summary>
              <pre
                style={{
                  background: '#020617',
                  padding: 8,
                  borderRadius: 6,
                  marginTop: 6,
                  color: '#cbd5e1',
                  overflowX: 'auto'
                }}
              >
                {JSON.stringify(request.args, null, 2)}
              </pre>
            </details>

            {/* Remember Choice for Tier 1 */}
            {request.can_remember && (
              <Checkbox
                checked={remember}
                onChange={(_, data) => setRemember(Boolean(data.checked))}
                label={`Remember this approval for folder: ${request.folder_path || 'this folder'}`}
              />
            )}
          </DialogContent>

          <DialogActions style={{ marginTop: 16 }}>
            <Button appearance="secondary" onClick={() => onRespond('denied', false)}>
              Deny
            </Button>
            <Button
              appearance="primary"
              style={{
                backgroundColor: isTier2 ? '#dc2626' : '#2563eb',
                color: '#fff'
              }}
              onClick={() => onRespond('approved', remember)}
            >
              Approve Action
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
};
