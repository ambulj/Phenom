import React from 'react';
import { Button } from '@fluentui/react-components';
import { DismissRegular } from '@fluentui/react-icons';

interface HistoryPanelProps {
  onClose: () => void;
  messages: Array<{ id: string; role: string; content: string; timestamp?: string }>;
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({ onClose, messages }) => {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: 16,
          borderBottom: '1px solid rgba(0, 82, 255, 0.25)'
        }}
      >
        <h2 style={{ fontSize: 16, fontWeight: 600, color: '#f8fafc', margin: 0 }}>Conversation History</h2>
        <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.length === 0 ? (
          <div style={{ color: '#64748b', fontSize: 14 }}>No messages recorded yet.</div>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              style={{
                background: m.role === 'user' ? 'rgba(0, 82, 255, 0.20)' : 'rgba(13, 17, 26, 0.85)',
                border: m.role === 'user' ? '1px solid rgba(0, 82, 255, 0.40)' : '1px solid rgba(0, 82, 255, 0.22)',
                borderRadius: 8,
                padding: '10px 14px',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: m.role === 'user' ? '#337aff' : '#CCFF00',
                  marginBottom: 4,
                  letterSpacing: 0.5
                }}
              >
                {m.role.toUpperCase()}
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.5, whiteSpace: 'pre-wrap', color: '#f8fafc' }}>{m.content}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
