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
      <DialogSurface
        style={{
          backgroundColor: '#080B10',
          border: '1px solid rgba(0, 82, 255, 0.45)',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.9), 0 0 25px rgba(0, 82, 255, 0.25)',
          borderRadius: 14
        }}
      >
        <DialogBody>
          <DialogTitle
            action={
              <Badge
                appearance="filled"
                color={isTier3 ? 'danger' : isTier2 ? 'severe' : 'warning'}
                size="medium"
                style={{
                  background: isTier3 || isTier2 ? '#EF4444' : '#0052FF',
                  color: '#ffffff',
                  fontWeight: 600
                }}
              >
                TIER {request.tier} {isTier2 ? 'DESTRUCTIVE / EXTERNAL' : 'REVERSIBLE CHANGE'}
              </Badge>
            }
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#f8fafc' }}>
              <WarningFilled style={{ color: isTier2 ? '#EF4444' : '#CCFF00', fontSize: 20 }} />
              Security Confirmation Required
            </div>
          </DialogTitle>

          <DialogContent style={{ display: 'flex', flexDirection: 'column', gap: 14, paddingTop: 12 }}>
            <div style={{ fontSize: 13, color: '#94a3b8' }}>
              Action requested: <strong style={{ color: '#CCFF00', fontFamily: 'Consolas, monospace' }}>{request.tool}</strong>
            </div>

            {/* Human Readable Preview */}
            <div
              style={{
                background: 'rgba(13, 17, 26, 0.85)',
                padding: '12px 16px',
                borderRadius: 8,
                border: '1px solid rgba(0, 82, 255, 0.25)',
                fontSize: 14,
                color: '#f8fafc',
                lineHeight: 1.5,
                boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.5)'
              }}
            >
              {request.preview}
            </div>

            {/* Arguments */}
            <details style={{ fontSize: 12, color: '#64748b', cursor: 'pointer' }}>
              <summary style={{ color: '#0052FF', fontWeight: 600 }}>View raw parameters</summary>
              <pre
                style={{
                  background: '#040609',
                  border: '1px solid rgba(0, 82, 255, 0.18)',
                  padding: 10,
                  borderRadius: 6,
                  marginTop: 6,
                  color: '#cbd5e1',
                  overflowX: 'auto',
                  fontFamily: 'Consolas, monospace',
                  fontSize: 11
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
            <Button
              appearance="secondary"
              onClick={() => onRespond('denied', false)}
              style={{
                background: 'rgba(13, 17, 26, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: '#f8fafc'
              }}
            >
              Deny
            </Button>
            <Button
              appearance="primary"
              style={{
                background: isTier2
                  ? '#EF4444'
                  : 'linear-gradient(135deg, #0052FF, #1a66ff)',
                borderColor: isTier2 ? '#EF4444' : '#0052FF',
                color: '#ffffff',
                fontWeight: 600,
                boxShadow: isTier2 ? '0 0 12px rgba(239, 68, 68, 0.4)' : '0 0 12px rgba(0, 82, 255, 0.4)'
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
