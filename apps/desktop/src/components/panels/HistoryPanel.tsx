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
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
        }}
      >
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Conversation History</h2>
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
                background: m.role === 'user' ? 'rgba(37, 99, 235, 0.15)' : 'rgba(30, 41, 59, 0.5)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 8,
                padding: '10px 14px'
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 600, color: m.role === 'user' ? '#60a5fa' : '#a855f7', marginBottom: 4 }}>
                {m.role.toUpperCase()}
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{m.content}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
